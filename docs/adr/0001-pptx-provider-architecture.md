# 0001. PPTX Provider Architecture

## Context
PPTX rendering currently only works when Microsoft Office is available on Windows systems.

## Decision
Introduce a provider pattern for PPTX→PDF conversion.

## Alternatives
- LibreOffice/OnlyOffice: require large office suites and heavy dependencies.
- python-pptx: lacks rendering support.

## Consequences
Ship a lightweight stub provider by default and offer an optional Microsoft Office-backed provider.
