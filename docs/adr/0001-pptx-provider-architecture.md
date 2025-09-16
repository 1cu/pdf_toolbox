# 0001. PPTX Provider Architecture

Status: Accepted
Date: 2024-05-20
Last updated: 2024-05-21
Deciders: Core maintainers (@1cu, @pdf-toolbox/maintainers)
Consulted: —
Tags: pptx, rendering, providers, plugin-architecture

See also: [ADR index](README.md), [Development guide](../../DEVELOPMENT.md#pptx-renderer-providers)

## Context

PPTX rendering currently only works when Microsoft Office is available on Windows systems.

Goals:

- Cross-platform PPTX→PDF and slide image rendering with pluggable backends.
- Headless execution suitable for CI, containers, and remote workers.
- Predictable fidelity with clear, actionable failure modes.

Quality bar:

- Rendering smoke tests cover representative decks (animations, fonts, video poster frames).
- Golden-file comparisons gate provider upgrades:
  - PDF: canonicalize (object stream order/fonts) and diff extracted text; allow ignorable metadata deltas.
  - Images: SSIM thresholds per format (e.g., JPEG ≥0.95, PNG/TIFF ≥0.99) with fixed DPI.
  - Record baselines per provider+version; bump baseline only via explicit review.
- Providers surface actionable error codes/messages when conversion diverges from the baseline.

Non-goals:

- PPTX authoring or editing functionality.
- Guaranteeing identical visual output across providers.
- Replacing specialized document services or viewers.

## Decision

Introduce a provider pattern for PPTX→PDF conversion.

Interface:

- Module: `pdf_toolbox.renderers.pptx`
- Base class: `BasePptxRenderer`
- Required methods:
  - `to_pdf(input_pptx: Path, output_path: Path | None = None, *, notes: bool = False, handout: bool = False, range_spec: str | None = None) -> Path`
    - Emits a PDF at `output_path` (or a generated temp path) and raises `PptxRenderingError` on failure.
    - Range selection:
      - `range_spec` grammar (1-based, inclusive): `(<n>|<n>-<m>|<n>-)(, ...)*` e.g., `1-3,5,7-`
      - Parsing MUST ignore ASCII whitespace around tokens and de-duplicate or merge overlapping ranges.
      - Indices MUST be ≥ 1; 0 or negative indices are invalid.
      - Invalid specs MUST raise `PptxRenderingError("invalid_range")`
      - Out-of-bounds indices are ignored if intersecting slides remain; otherwise raise `PptxRenderingError("empty_selection")`
    - `notes` and `handout` are mutually exclusive; if both are True, raise `UnsupportedOptionError` with `error.code == "conflicting_options"`.
    - Implementations MUST document how `notes` and `handout` map to backend output.
  - `to_images(input_pptx: Path, output_dir: Path | None = None, *, format: Literal["png", "jpeg", "tiff"] = "jpeg", dpi: int = 150, slides: Sequence[int] | None = None) -> list[Path]`
    - Produces one image per slide (or selected slide indices) in `output_dir` and returns ordered file paths.
    - Conventions (MUST):
      - Slide indexing is 1-based.
      - Filenames: `slide-<NNN>.<ext>` where the pad width is `max(3, ceil(log10(total_slides + 1)))` for the input deck (e.g., 42 slides → width 3; 1,234 slides → width 4). Extension MUST match `format` (`jpeg`, not `jpg`).
      - When `slides` is `None`, return value is sorted by slide index ascending. When `slides` is provided, return paths in the order of `slides` after de-duplicating indices.
      - Unsupported `format`/`dpi` MUST raise `PptxRenderingError("unsupported_option")`.
    - Implementations MUST document DPI bounds and any backend-specific limits.
  - `capabilities() -> Capabilities`
  - `probe() -> bool`

Where `Capabilities` includes (minimum):

```python
from typing import Literal, TypedDict

class Capabilities(TypedDict, total=False):
    platforms: list[Literal["windows", "linux", "macos"]]
    outputs: list[Literal["pdf", "png", "jpeg", "tiff"]]  # formerly `supports`
    headless: bool                 # TRUE implies UI not required
    needs_ui: bool                 # TRUE implies headless is FALSE
    vendor: str | None             # e.g., "Microsoft Office", "LibreOffice", "Aspose"
    version: str | None            # provider version string
    supports_notes: bool
    supports_handout: bool
    supports_ranges: bool
    min_dpi: int | None
    max_dpi: int | None
    needs_network: bool
    max_page_count: int | None
    max_file_size_mb: int | None
    notes: str | None
```

Invariants:

- If `headless` is True, `needs_ui` MUST be False. If `needs_ui` is True, `headless` MUST be False. If both are omitted, treat the provider as unknown and avoid selecting it in `auto` mode for headless environments.

Capabilities objects MUST remain backwards compatible; new optional keys extend the schema without breaking older providers.

Discovery:

- Python entry points group: `pdf_toolbox.pptx_renderers`
- Entry point names follow `vendor[_flavor]` (for example, `ms_office`, `libreoffice_uno`) and MUST be unique.

Selection:

- Config key: `pptx_renderer`; accepted values match entry point names.
- Accepted special values:
  - `null` → selects `NullRenderer`, an explicit stub with guidance.
  - `auto` → selection algorithm:
    1. Filter providers by platform compatibility.
    1. If running headless (no DISPLAY/Wayland/GUI), exclude providers where `needs_ui` is True.
    1. Exclude providers with `needs_network` unless `allow_network_egress` is explicitly enabled.
    1. Respect configured allow and deny lists.
    1. Probe remaining providers in priority order and select the first where `probe() == True`.
- Default configuration: `auto` in production; `null` is available for development scenarios where explicit guidance is preferable.
- Providers must document fallback order, prerequisites, and user-facing error messaging.

Notes:

- `NullRenderer.probe()` MUST return `False` and MUST be excluded from `auto` selection.
- Provider probe order is configurable; document default priority and how to override it.

## Alternatives

- LibreOffice (headless/UNO) or OnlyOffice: heavy dependencies, reasonable fidelity, container-friendly but large images.
- Gotenberg or `soffice` sidecars: operationally convenient; add process/network boundaries and more moving parts.
- Aspose.Slides (commercial): high fidelity and automation support; licensing costs and vendor lock-in.
- Cloud conversion APIs: zero local dependencies; privacy/compliance risks and unpredictable latency.
- python-pptx: parsing only; no rendering support.

## Consequences

Ship a lightweight stub provider by default and offer an optional Microsoft Office provider. Stub and local providers MUST NOT perform network egress or upload content; any cloud-backed provider requires explicit opt-in and clear warnings.

Errors:

- All providers MUST raise `PptxRenderingError` (and well-known subclasses like `UnsupportedOptionError`, `BackendCrashedError`, `TimeoutError`) and set a stable `error.code` from this canonical set:
  - `invalid_range`, `empty_selection`, `unsupported_option`, `conflicting_options`, `backend_crashed`, `timeout`, `unavailable`, `permission_denied`, `resource_limits_exceeded`.
  - Subclass names are advisory; clients MUST rely on `error.code`.

Network posture:

- Default is no network egress; any egress-capable provider MUST require an explicit config flag and display a privacy notice.

Operational considerations:

- Provider instances MUST either support concurrent use across threads/processes or document that they are single-use and require one instance per render.
- Enforce per-render timeouts and bounded concurrency to guard against hung conversions.
- Enforce input limits (file size, slide count) and configurable memory/CPU ceilings per task.
- Isolate providers with subprocesses or service boundaries when possible and sanitize temporary assets.
- Implement structured retries with jittered backoff for transient failures and circuit breakers per provider.
- Account for Windows COM constraints: single-threaded apartments, foreground window quirks, and DCOM hardening requirements.
- Emit structured logs (provider name, version, duration, page count, result, error.code) and metrics.
- Do NOT log document contents or slide thumbnails; log only metadata and SHA-256 hashes of filenames (no paths).
- Include a request/job correlation ID in logs and metrics.
- Provide clear UX when no provider is available or misconfigured, including remediation steps.
- Provide liveness/readiness health checks and periodic `probe()` executions to decay unhealthy providers from rotation.
