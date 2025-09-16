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
- Golden-file comparisons (PDF text diff and image pixel SSIM ≥0.95) gate provider upgrades.
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
    - Emits a PDF at `output_path` (or a generated temp path) and raises `PptxRenderingError` on failure. Implementations document how `notes`, `handout`, and slide range selection map to the backend.
  - `to_images(input_pptx: Path, output_dir: Path | None = None, *, format: Literal["png", "jpeg", "tiff"] = "jpeg", dpi: int = 150, slides: Sequence[int] | None = None) -> list[Path]`
    - Produces one image per slide (or selected slide indices) in `output_dir` and returns ordered file paths. Implementations must document supported formats, DPI bounds, naming conventions, and failure behavior.
  - `capabilities() -> Capabilities`
  - `probe() -> bool`

Where `Capabilities` includes (minimum):

```python
from typing import Literal, TypedDict

class Capabilities(TypedDict, total=False):
    platforms: list[Literal["windows", "linux", "macos"]]
    supports: list[Literal["pdf", "png", "jpeg", "tiff"]]
    headless: bool
    needs_ui: bool
    needs_network: bool
    max_page_count: int | None
    max_file_size_mb: int | None
    notes: str | None
```

Capabilities objects MUST remain backwards compatible; new optional keys extend the schema without breaking older providers.

Discovery:

- Python entry points group: `pdf_toolbox.pptx_renderers`
- Entry point names follow `vendor[_flavor]` (for example, `ms_office`, `libreoffice_uno`, `gotenberg_v7`) and MUST be unique.

Selection:

- Config key: `pptx_renderer`; accepted values match entry point names.
- Accepted special values:
  - `null` → selects `NullRenderer`, an explicit stub with guidance.
  - `auto` → probes providers in priority order and selects the first healthy result.
- Default configuration: `auto` in production; `null` is available for development scenarios where explicit guidance is preferable.
- Providers must document fallback order, prerequisites, and user-facing error messaging.

## Alternatives

- LibreOffice (headless/UNO) or OnlyOffice: heavy dependencies, reasonable fidelity, container-friendly but large images.
- Gotenberg or `soffice` sidecars: operationally convenient; add process/network boundaries and more moving parts.
- Aspose.Slides (commercial): high fidelity and automation support; licensing costs and vendor lock-in.
- Cloud conversion APIs: zero local dependencies; privacy/compliance risks and unpredictable latency.
- python-pptx: parsing only; no rendering support.

## Consequences

Ship a lightweight stub provider by default and offer an optional Microsoft Office provider. Stub and local providers MUST NOT perform network egress or upload content; any cloud-backed provider requires explicit opt-in and clear warnings.

Operational considerations:

- Enforce per-render timeouts and bounded concurrency to guard against hung conversions.
- Enforce input limits (file size, slide count) and configurable memory/CPU ceilings per task.
- Isolate providers with subprocesses or service boundaries when possible and sanitize temporary assets.
- Implement structured retries with jittered backoff for transient failures and circuit breakers per provider.
- Account for Windows COM constraints: single-threaded apartments, foreground window quirks, and DCOM hardening requirements.
- Emit structured logs (provider name, version, duration, page count, result) and metrics for success/failure rates.
- Provide clear UX when no provider is available or misconfigured, including remediation steps.
- Provide liveness/readiness health checks and periodic `probe()` executions to decay unhealthy providers from rotation.
