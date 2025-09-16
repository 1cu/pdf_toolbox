# 0001. PPTX Provider Architecture

Status: Accepted
Date: 2024-05-20
Deciders: Core maintainers (@1cu, @pdf-toolbox/maintainers)
Consulted: —
Tags: pptx, rendering, providers, plugin-architecture

## Context

PPTX rendering currently only works when Microsoft Office is available on Windows systems.

Goals:

- Cross-platform PPTX→PDF and image rendering with pluggable backends.
- Headless execution suitable for CI, containers, and remote workers.
- Predictable fidelity with clear, actionable failure modes.

Non-goals:

- PPTX authoring or editing functionality.
- Guaranteeing identical visual output across providers.
- Replacing specialized document services or viewers.

## Decision

Introduce a provider pattern for PPTX→PDF conversion.

Interface:

- Module: `pdf_toolbox.renderers.pptx`
- Base class: `BasePptxRenderer`
- Required methods: `render_to_pdf(input: Path, output: Path) -> None`, `capabilities() -> dict`, `probe() -> bool`

Discovery:

- Python entry points group: `pdf_toolbox.pptx_renderers`
- Entry point name equals the provider key (for example, `ms_office`, `libreoffice`)

Selection:

- Config key: `pptx_renderer`; accepted values match entry point names.
- Default `null` selects `NullRenderer`, which surfaces actionable guidance.
- Providers must document fallback order, prerequisites, and user-facing error messaging.

## Alternatives

- LibreOffice (headless/UNO) or OnlyOffice: heavy dependencies, reasonable fidelity, container-friendly but large images.
- Gotenberg or `soffice` sidecars: operationally convenient; add process/network boundaries and more moving parts.
- Aspose.Slides (commercial): high fidelity and automation support; licensing costs and vendor lock-in.
- Cloud conversion APIs: zero local dependencies; privacy/compliance risks and unpredictable latency.
- python-pptx: parsing only; no rendering support.

## Consequences

Ship a lightweight stub provider by default and offer an optional Microsoft Office provider.

Operational considerations:

- Enforce per-render timeouts and bounded concurrency to guard against hung conversions.
- Isolate providers with subprocesses or service boundaries when possible and sanitize temporary assets.
- Account for Windows COM constraints: single-threaded apartments, foreground window quirks, and DCOM hardening requirements.
- Emit structured logs (provider name, version, duration, page count, result) and metrics for success/failure rates.
- Provide clear UX when no provider is available or misconfigured, including remediation steps.
