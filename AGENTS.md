# Agent Guidelines

This file provides general instructions for all contributors. Directory-specific instructions live in `AGENTS.md` files in subdirectories such as `src/pdf_toolbox`, `tests`, and `scripts`. When working on a file, apply the rules from this file and any nested `AGENTS.md`.

## Environment

- Install dependencies with `pip install -e '.[dev]'`.
- Install git hooks via `pre-commit install`.
- Export `QT_QPA_PLATFORM=offscreen` when running pre-commit or tests.

## Workflow

- Run `pre-commit run --all-files` before every commit. The hooks format, lint, run tests, and perform security checks. Allow them to finish even if they take a while.
- Use `pre-commit run format|lint|tests` to run subsets when needed.
- If hooks modify files, stage the changes and re-run `pre-commit run --files <file>`.
- Bump the `version` in `pyproject.toml` once per pull request.
- Write descriptive commit messages: short imperative summary (≤72 characters), blank line, then details.

## Quality

- Maintain at least 95% test coverage for every module; modules excluded in
  the coverage configuration in `pyproject.toml` are exempt.
- Use clear, descriptive names for functions and variables.

See the `AGENTS.md` in each subdirectory for additional guidance. The most deeply nested instructions take precedence.

# Linting-Policy: Fix, don’t silence

**Grundsatz**

- Erst Code reparieren, nicht die Regel ausschalten.
- Linter helfen, Fehler früh zu finden und Lesbarkeit zu sichern.

**Verboten (sofern nicht unter „Ausnahmen“ dokumentiert):**

- `# noqa`, `# ruff: noqa`, `# noqa: PLR...`, `# type: ignore` ohne Begründung.
- Per-Datei-/Block-Disables: `# ruff: noqa`, `# ruff: noqa: <codes>`, `flake8: noqa`, `pylint: disable=...`.
- Änderungen an `pyproject.toml`, die Regeln absenken/entfernen, um einen einzelnen Befund zu „grün“ zu machen.

**Erwartetes Vorgehen**

1. Warnung verstehen (Regelbeschreibung lesen).
1. Code vereinfachen/refactoren (z. B. Komplexität senken statt `PLR0915` zu muten).
1. Typen/Nullpfade absichern statt `type: ignore`.
1. Tests anpassen/ergänzen, falls das Refactoring Verhalten ändert.
1. Nur wenn technisch nicht lösbar: Ausnahme prüfen (siehe unten).

**Ausnahmen (nur in seltenen Fällen)**
Erlaubt ist ein Disable **nur**, wenn alle Punkte erfüllt sind:

- **Begründung** direkt am Code in 1–2 Sätzen: *warum* die Regel hier nicht sinnvoll ist.
- **Scope minimal** (eine Zeile, kein Datei- oder Modul-Disable).
- **Ticket/Issue-Referenz** (z. B. `# noqa: PLR0915  # see #123: Algorithmus bewusst unrolled for perf on large PDFs`).
- **Follow-up**: Wenn es ein temporärer Workaround ist, verlinke ein Issue mit Plan (Deadline oder Kriterien).

**Beispiele**

- ✅ Gut:

  ```python
  def _scale(img, target):  # zyklomatische Komplexität < 10
      ...
  ```

  (Regel erfüllt durch Refactoring.)

- ✅ Seltene Ausnahme:

  ```python
  result: Any = json.loads(raw)  # noqa: ANN401  # see #456: Fremd-API liefert heterogene Strukturen; Adapter folgt.
  ```

- ❌ Schlecht:

  ```python
  # ruff: noqa
  def build_form(...):
      ...
  ```

  (pauschales Abschalten des Linters)

**Änderungen an Linter-Konfiguration**

- Regeln dürfen nur nach Team-Entscheid geändert werden (PR mit Begründung, Alternativen, Impact).
- Kein Herabsetzen von Schweregraden als Workaround.

**PR-Checkliste (bitte im PR-Template abhaken)**

- [ ] Alle neuen/geänderten Dateien linten sauber ohne neue Disables.
- [ ] Kein Anstieg von `noqa`/`type: ignore` in der Codebasis.
- [ ] Wenn Disable nötig: Begründung + Issue-Link vorhanden, Scope minimal.
- [ ] Tests grün; neue Tests für Refactorings vorhanden.

**Review-Hinweise**

- Lehnt PRs ab, die Regeln ohne fundierte Begründung abschalten.
- Fordert Refactoring-Vorschläge ein (Komplexität, Duplication, Typen).

______________________________________________________________________

## Kurzleitfaden für häufige Ruff-Regeln

- `PLR0915` (zu komplex): Funktion splitten, Helfer extrahieren, frühe Returns.
- `ANN401` (Any): präzise Typen oder Adapter; nur ausnahmsweise `Any` mit Begründung.
- `E/F` (Syntax/Name): Fehler fixen, keine Ausnahmen.
- `I` (Import sort): Imports ordnen, nicht deaktivieren.
