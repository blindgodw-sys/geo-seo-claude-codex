# Codex Port Plan

## Goal

Port the GEO-SEO Claude Code skill bundle to a Codex-native skill installation
while preserving functional behavior after excluding inherent LLM runtime
differences.

## Success Criteria

1. Codex can discover the `geo` skill through `codex debug prompt-input`.
2. The Codex installation lives under `${CODEX_HOME:-~/.codex}/skills`.
3. Existing Claude Code files remain intact; Codex-specific entrypoints are
   additive.
4. Commands keep the original user-facing shape:
   - `geo audit <url>`
   - `geo quick <url>`
   - `geo citability <url>`
   - `geo crawlers <url>`
   - `geo llmstxt <url>`
   - `geo brands <url>`
   - `geo platforms <url>`
   - `geo schema <url>`
   - `geo technical <url>`
   - `geo content <url>`
   - `geo report <url>`
   - `geo report-pdf <url>`
   - `geo prospect ...`
   - `geo proposal <domain>`
   - `geo compare <domain>`
   - `geo update`
5. Output file names match the original project:
   - `GEO-AUDIT-REPORT.md`
   - `GEO-CITABILITY-SCORE.md`
   - `GEO-CRAWLER-ACCESS.md`
   - `GEO-LLMSTXT-ANALYSIS.md` or `llms.txt` plus
     `GEO-LLMSTXT-GENERATION.md`
   - `GEO-BRAND-MENTIONS.md`
   - `GEO-PLATFORM-OPTIMIZATION.md`
   - `GEO-SCHEMA-REPORT.md`
   - `GEO-TECHNICAL-AUDIT.md`
   - `GEO-CONTENT-ANALYSIS.md`
   - `GEO-CLIENT-REPORT.md`
   - `GEO-REPORT.html`
   - `GEO-REPORT.pdf` when a headless browser is available
6. Runtime data for CRM-style commands remains under `~/.geo-prospects/` by
   default, with `GEO_PROSPECTS_HOME` available for isolated test runs.
7. No uninstall/update flow deletes files directly. Files that would be
   replaced or removed are moved to a timestamped temporary backup directory.

## Implementation Approach

### Codex Skill Layer

Create an additive Codex entrypoint at `codex/geo/SKILL.md`. It routes command
requests to a deterministic CLI:

```bash
~/.codex/skills/geo/scripts/geo_cli.py <command> <args>
```

The main skill remains concise and points Codex to the CLI for repeatable
operations. The original `skills/geo-*` skill files are copied into Codex too,
with Claude paths patched to Codex paths, so focused sub-skill prompts remain
discoverable.

### Installer

Add `codex-install.sh`:

1. Resolve source directory.
2. Create `${CODEX_HOME:-~/.codex}/skills/geo`.
3. Copy scripts, schema, templates, and the Codex main skill.
4. Copy existing sub-skills to `${CODEX_HOME:-~/.codex}/skills/geo-*`.
5. Copy original agent rubrics to `${CODEX_HOME:-~/.codex}/skills/geo/agents`.
6. Patch installed markdown paths and browser-tool wording to Codex equivalents.
7. Create an isolated venv under `~/.codex/skills/geo/.venv`.
8. Install `requirements.txt` into the venv.
9. Pin script shebangs to the venv Python.
10. Verify key files and print a `codex debug prompt-input` command.

### CLI Layer

Add `scripts/geo_cli.py` to provide a stable command surface for Codex skill
execution and smoke testing. It reuses existing helpers:

- `fetch_page.py`
- `citability_scorer.py`
- `brand_scanner.py`
- `llmstxt_generator.py`

The CLI generates the same report file names and keeps the original scoring
weights. It produces deterministic evidence and draft sections. LLM-judged
synthesis uses the original agent rubrics copied into the installed Codex skill,
so the deterministic CLI output and the original review criteria are both
available during Codex execution.

### Web Access Mapping

Static pages use `requests` through the existing Python utilities. Dynamic,
login-gated, screenshot, or browser-rendered checks should be performed by
Codex with `web-access` or Playwright, then merged into reports when needed.

### PDF Mapping

The original current PDF path uses pandoc and macOS Chrome. The Codex port
supports:

1. `pandoc` plus discovered Chrome/Chromium/Edge when available.
2. Direct HTML generation plus discovered Chrome/Chromium/Edge as fallback.

No ReportLab dependency is introduced.

## Known Source Gaps To Close

- `/geo page` is listed in `geo/SKILL.md` but has no source skill. The Codex CLI
  implements it as a single-page audit alias that writes `GEO-PAGE-ANALYSIS.md`.
- `/geo quick` has no standalone source skill. The Codex CLI implements it as a
  lightweight snapshot.
- `docs/commands-reference.md` contains stale ReportLab references for PDF.
  The Codex port follows `skills/geo-report-pdf/SKILL.md`, which is the current
  pandoc + Chrome path.

## Full Test Target

Use `https://www.lacewigsbuy.com` for full-surface testing.

The full test must run every command listed in the success criteria, record
created files, and validate that reports contain target-domain evidence rather
than placeholder-only output. It must also place CRM test data inside the run
directory instead of touching the default `~/.geo-prospects/` state.
