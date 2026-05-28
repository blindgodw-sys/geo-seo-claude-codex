<p align="center">
  <img src="assets/banner.svg" alt="GEO-SEO Codex Skill" width="900"/>
</p>

<p align="center">
  <strong>GEO-first, SEO-supported.</strong> Optimize websites for AI-powered search engines<br/>
  (ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews) while maintaining traditional SEO foundations.
</p>

<p align="center">
  <strong>GEO 优先，SEO 辅助。</strong> 面向 AI 搜索引擎优化网站可见性<br/>
  （ChatGPT、Claude、Perplexity、Gemini、Google AI Overviews），同时保留传统 SEO 基础。
</p>

<p align="center">
  AI search is eating traditional search. This tool optimizes for where traffic is going, not where it was.
</p>

<p align="center">
  AI 搜索正在重塑传统搜索流量。本工具优化的是流量正在迁移到的 AI 搜索场景。
</p>

---

## Codex Native Fork / Codex 原生改写版本

中文说明：本仓库基于开源项目
[`zubair-trabzada/geo-seo-claude`](https://github.com/zubair-trabzada/geo-seo-claude)
改编，原项目采用 MIT License（MIT 许可证）。本仓库将原 Claude Code
技能包改写为 Codex 可直接安装和调用的技能包，并保留原项目版权声明和
MIT 许可证文本。

本仓库由 `blindgodw-sys` 独立维护，不是上游项目的官方发布版本。完整改写
说明、合规说明、验证记录见
[`docs/codex-port-notes.md`](docs/codex-port-notes.md)。

This repository is a Codex-native adaptation of the original open-source
project [`zubair-trabzada/geo-seo-claude`](https://github.com/zubair-trabzada/geo-seo-claude),
which is distributed under the MIT License.

The original copyright and MIT License notice are preserved in
[`LICENSE`](LICENSE). This fork is maintained independently by
`blindgodw-sys`; it is not an official release of the upstream project.

What changed in this fork:

- installs into `~/.codex/skills` instead of Claude Code directories;
- adds Codex-native skill entrypoints under `codex/`;
- adds `codex-install.sh` for one-command Codex installation;
- adds `scripts/geo_cli.py` as the repeatable command adapter;
- keeps the original skill bundle, agents, schema templates, and core GEO logic;
- adds Chinese report-output rules for user-facing reports.

See [`docs/codex-port-notes.md`](docs/codex-port-notes.md) for the full
modification list, design notes, validation record, and upstream attribution.

本版本主要改写内容：

- 安装位置从 Claude Code 目录改为 `~/.codex/skills`；
- 在 `codex/` 下新增 Codex 原生技能入口；
- 新增 `codex-install.sh`，支持一条命令安装；
- 新增 `scripts/geo_cli.py`，作为可重复执行的命令适配器；
- 保留原技能包、子智能体、结构化数据模板和核心 GEO 逻辑；
- 增加中文报告输出规则，面向用户的报告默认支持中文。

---

## Why GEO Matters (2026)

| Metric | Value |
|--------|-------|
| GEO services market | $850M+ (projected $7.3B by 2031) |
| AI-referred traffic growth | +527% year-over-year |
| AI traffic conversion rate vs organic | 4.4x higher |
| Gartner: search traffic drop by 2028 | -50% |
| Brand mentions vs backlinks for AI | 3x stronger correlation |
| Marketers investing in GEO | Only 23% |

---

## Quick Start

### One-Command Codex Install (macOS/Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/blindgodw-sys/geo-seo-claude-codex/main/codex-install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/blindgodw-sys/geo-seo-claude-codex.git
cd geo-seo-claude-codex
./codex-install.sh
```

### Windows

Use WSL or Git Bash. The Codex installer targets Unix-style paths and installs
under `~/.codex/skills`.

### Requirements

- Python 3.8+ (on Debian/Ubuntu also `python3-venv`)
- Codex CLI
- Git
- Optional: [`uv`](https://docs.astral.sh/uv/) — if present, the installer uses it for a faster dependency install
- Optional: Playwright (for screenshots)

### Isolated install

Python dependencies are installed into a dedicated virtual environment at
`~/.codex/skills/geo/.venv/`. Your system Python is **not** touched, and
uninstalling the skill removes the venv together with the rest of the files.

Skill and agent files reference that venv directly, so the tool works
regardless of what `python3` resolves to on your `PATH`.

---

## Commands

Open Codex and use these commands:

| Command | What It Does |
|---------|-------------|
| `geo audit <url>` | Full GEO + SEO audit |
| `geo quick <url>` | 60-second GEO visibility snapshot |
| `geo citability <url>` | Score content for AI citation readiness |
| `geo crawlers <url>` | Check AI crawler access (robots.txt) |
| `geo llmstxt <url>` | Analyze or generate llms.txt |
| `geo brands <url>` | Scan brand mentions across AI-cited platforms |
| `geo platforms <url>` | Platform-specific optimization |
| `geo schema <url>` | Structured data analysis & generation |
| `geo technical <url>` | Technical SEO audit |
| `geo content <url>` | Content quality & E-E-A-T assessment |
| `geo report <url>` | Generate client-ready GEO report |
| `geo report-pdf <url>` | Generate HTML and PDF report |

---

## Architecture

```
geo-seo-claude/
├── codex/                       # Codex-native skill entrypoints
│   ├── geo/
│   └── geo-update/
├── geo/                          # Main skill orchestrator
│   └── SKILL.md                  # Primary skill file with commands & routing
├── skills/                       # 13 specialized sub-skills
│   ├── geo-audit/                # Full audit orchestration & scoring
│   ├── geo-citability/           # AI citation readiness scoring
│   ├── geo-crawlers/             # AI crawler access analysis
│   ├── geo-llmstxt/              # llms.txt standard analysis & generation
│   ├── geo-brand-mentions/       # Brand presence on AI-cited platforms
│   ├── geo-platform-optimizer/   # Platform-specific AI search optimization
│   ├── geo-schema/               # Structured data for AI discoverability
│   ├── geo-technical/            # Technical SEO foundations
│   ├── geo-content/              # Content quality & E-E-A-T
│   ├── geo-report/               # Client-ready markdown report generation
│   ├── geo-report-pdf/           # Professional PDF report with charts
│   ├── geo-prospect/             # CRM-lite prospect pipeline management
│   ├── geo-proposal/             # Auto-generate client proposals
│   └── geo-compare/              # Monthly delta tracking & progress reports
├── agents/                       # 5 parallel subagents
│   ├── geo-ai-visibility.md      # GEO audit, citability, crawlers, brands
│   ├── geo-platform-analysis.md  # Platform-specific optimization
│   ├── geo-technical.md          # Technical SEO analysis
│   ├── geo-content.md            # Content & E-E-A-T analysis
│   └── geo-schema.md             # Schema markup analysis
├── scripts/                      # Python utilities
│   ├── fetch_page.py             # Page fetching & parsing
│   ├── citability_scorer.py      # AI citability scoring engine
│   ├── brand_scanner.py          # Brand mention detection
│   ├── llmstxt_generator.py      # llms.txt validation & generation
│   └── geo_cli.py                # Codex CLI command adapter
├── schema/                       # JSON-LD templates
│   ├── organization.json         # Organization schema (with sameAs)
│   ├── local-business.json       # LocalBusiness schema
│   ├── article-author.json       # Article + Person schema (E-E-A-T)
│   ├── software-saas.json        # SoftwareApplication schema
│   ├── product-ecommerce.json    # Product schema with offers
│   └── website-searchaction.json # WebSite + SearchAction schema
├── codex-install.sh              # One-command Codex installer
├── uninstall.sh                  # Uninstaller
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## Data Storage

The CRM and reporting skills (`geo prospect`, `geo proposal`, `geo compare`) store runtime data outside the Codex directory:

```
~/.geo-prospects/
├── prospects.json              # Client/prospect pipeline data
├── proposals/                  # Generated proposal documents
│   └── <domain>-proposal-<date>.md
└── reports/                    # Monthly delta reports
    └── <domain>-monthly-<YYYY-MM>.md
```

This directory is **not removed** by the uninstaller — delete it manually if you no longer need your prospect data.

---

## How It Works

### Full Audit Flow

When you run `geo audit https://example.com`:

1. **Discovery** — Fetches homepage, detects business type, crawls sitemap
2. **Parallel Analysis** — Launches 5 subagents simultaneously:
   - AI Visibility (citability, crawlers, llms.txt, brand mentions)
   - Platform Analysis (ChatGPT, Perplexity, Google AIO readiness)
   - Technical SEO (Core Web Vitals, SSR, security, mobile)
   - Content Quality (E-E-A-T, readability, freshness)
   - Schema Markup (detection, validation, generation)
3. **Synthesis** — Aggregates scores, generates composite GEO Score (0-100)
4. **Report** — Outputs prioritized action plan with quick wins

### Scoring Methodology

| Category | Weight |
|----------|--------|
| AI Citability & Visibility | 25% |
| Brand Authority Signals | 20% |
| Content Quality & E-E-A-T | 20% |
| Technical Foundations | 15% |
| Structured Data | 10% |
| Platform Optimization | 10% |

---

## Key Features

### Citability Scoring
Analyzes content blocks for AI citation readiness. Optimal AI-cited passages are 134-167 words, self-contained, fact-rich, and directly answer questions.

### AI Crawler Analysis
Checks robots.txt for 14+ AI crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.) and provides specific allow/block recommendations.

### Brand Mention Scanning
Brand mentions correlate 3x more strongly with AI visibility than backlinks. Scans YouTube, Reddit, Wikipedia, LinkedIn, and 7+ other platforms.

### Platform-Specific Optimization
Only 11% of domains are cited by both ChatGPT and Google AI Overviews for the same query. Provides tailored recommendations per platform.

### llms.txt Generation
Generates the emerging llms.txt standard file that helps AI crawlers understand your site structure.

### Client-Ready Reports
Generates professional GEO reports in markdown or PDF format. PDF reports include score gauges, bar charts, platform readiness visualizations, color-coded tables, and prioritized action plans — ready to deliver to clients.

---

## Use Cases

- **GEO Agencies** — Run client audits and generate deliverables
- **Marketing Teams** — Monitor and improve AI search visibility
- **Content Creators** — Optimize content for AI citations
- **Local Businesses** — Get found by AI assistants
- **SaaS Companies** — Improve entity recognition across AI platforms
- **E-commerce** — Optimize product pages for AI shopping recommendations

---

## Uninstall

```bash
rm -rf ~/.codex/skills/geo ~/.codex/skills/geo-*
```

Runtime CRM data in `~/.geo-prospects/` is not removed by the installer or this manual uninstall command.

---

## Want to Turn This Into a Business?

The tool is free. Learning how to monetize it is where the community comes in.

**[Join the AI Workshop Community →](https://skool.com/aiworkshop)**

Inside you'll get:
- **Video walkthroughs** — Step-by-step setup, running audits, reading results
- **Client acquisition playbook** — How to find prospects, pitch GEO services, and close deals
- **Live office hours** — Bring your audit results, get direct help
- **GEO agency pricing & templates** — Proposal docs, cold outreach scripts, onboarding workflows

GEO agencies charge $2K–$12K/month. This tool does the audit. The community teaches you how to sell it.

---





## License

MIT License

---

## Contributing

Contributions welcome!

---

Built for the AI search era.
