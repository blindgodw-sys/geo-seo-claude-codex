---
name: geo
description: Codex-native GEO and SEO audit tool for AI search visibility. Use for geo audit, geo quick, geo citability, geo crawlers, geo llmstxt, geo brands, geo platforms, geo schema, geo technical, geo content, geo report, geo report-pdf, geo prospect, geo proposal, geo compare, or geo update requests against a website URL or domain.
---

# GEO-SEO for Codex

This is the Codex-native entrypoint for the GEO-SEO toolkit. It preserves the
original `/geo ...` command surface by routing repeatable work through the
installed CLI:

```bash
~/.codex/skills/geo/scripts/geo_cli.py <command> <args>
```

If `CODEX_HOME` is set, use:

```bash
"${CODEX_HOME}/skills/geo/scripts/geo_cli.py" <command> <args>
```

## Evidence And Rubrics

The CLI produces deterministic evidence, report files, and CRM artifacts. For
LLM-judged synthesis, use the original project rubrics installed at:

- `~/.codex/skills/geo/agents/geo-ai-visibility.md`
- `~/.codex/skills/geo/agents/geo-content.md`
- `~/.codex/skills/geo/agents/geo-platform-analysis.md`
- `~/.codex/skills/geo/agents/geo-schema.md`
- `~/.codex/skills/geo/agents/geo-technical.md`

Load only the relevant agent file when the user asks for narrative analysis,
prioritized recommendations, platform interpretation, schema review, content
quality review, or technical SEO review.

## Report Language

All generated reports, summaries, recommendations, and user-facing analysis
must be written in Chinese. When an English product name, file standard, API,
crawler name, platform name, or technical term is necessary, keep the English
term and add a Chinese explanation in parentheses on first use, for example
`GEO（生成式引擎优化）`, `llms.txt（大模型说明文件）`, and `Schema（结构化数据）`.

## Command Map

| User command | CLI command |
|---|---|
| `/geo audit <url>` | `geo_cli.py audit <url>` |
| `/geo page <url>` | `geo_cli.py page <url>` |
| `/geo quick <url>` | `geo_cli.py quick <url>` |
| `/geo citability <url>` | `geo_cli.py citability <url>` |
| `/geo crawlers <url>` | `geo_cli.py crawlers <url>` |
| `/geo llmstxt <url>` | `geo_cli.py llmstxt <url>` |
| `/geo brands <url>` | `geo_cli.py brands <url>` |
| `/geo platforms <url>` | `geo_cli.py platforms <url>` |
| `/geo schema <url>` | `geo_cli.py schema <url>` |
| `/geo technical <url>` | `geo_cli.py technical <url>` |
| `/geo content <url>` | `geo_cli.py content <url>` |
| `/geo report <url>` | `geo_cli.py report <url>` |
| `/geo report-pdf <url>` | `geo_cli.py report-pdf <url>` |
| `/geo prospect ...` | `geo_cli.py prospect ...` |
| `/geo proposal <domain>` | `geo_cli.py proposal <domain>` |
| `/geo compare <domain>` | `geo_cli.py compare <domain>` |
| `/geo update` | `geo_cli.py update` |
| `/geo full-test <url>` | `geo_cli.py full-test <url>` |

The user may include the leading slash. Treat `/geo audit <url>` and
`geo audit <url>` as equivalent.

## Workflow

1. Normalize the URL or domain.
2. Run the matching CLI command from the current working directory unless the
   user asks for a different output directory.
3. Read the generated report and, when needed, the relevant installed agent
   rubric before giving analysis, summary, or next steps.
4. For dynamic pages, login-gated checks, screenshots, or browser-only state,
   use `web-access` for simple browser retrieval and Playwright for complex
   interaction. Merge those observations into the generated report when needed.
5. Do not delete generated or installed files. Move unwanted files to a
   timestamped temp directory if cleanup is requested.

## Output Files

The CLI writes the original project file names:

- `GEO-AUDIT-REPORT.md`
- `GEO-PAGE-ANALYSIS.md`
- `GEO-CITABILITY-SCORE.md`
- `GEO-CRAWLER-ACCESS.md`
- `GEO-LLMSTXT-ANALYSIS.md`
- `GEO-LLMSTXT-GENERATION.md`
- `llms.txt`
- `GEO-BRAND-MENTIONS.md`
- `GEO-PLATFORM-OPTIMIZATION.md`
- `GEO-SCHEMA-REPORT.md`
- `GEO-TECHNICAL-AUDIT.md`
- `GEO-CONTENT-ANALYSIS.md`
- `GEO-CLIENT-REPORT.md`
- `GEO-REPORT.html`
- `GEO-REPORT.pdf`

CRM-style commands store runtime data under `~/.geo-prospects/`, matching the
original project, unless `GEO_PROSPECTS_HOME` is set. The `full-test` command
uses an isolated CRM directory inside its test run folder.

## Validation

For installation checks:

```bash
codex debug prompt-input 'geo audit https://example.com'
```

The `geo` skill should appear in the model-visible skill list.

For a full surface test:

```bash
~/.codex/skills/geo/scripts/geo_cli.py full-test https://www.lacewigsbuy.com
```
