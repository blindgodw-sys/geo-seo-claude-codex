# Codex Port Notes / Codex 改写说明

## 中文说明

本文档说明本仓库如何从上游开源项目
[`zubair-trabzada/geo-seo-claude`](https://github.com/zubair-trabzada/geo-seo-claude)
改写为 Codex 可安装、可调用、可验证的 GEO/SEO 技能包。

### 来源与合规

- 上游项目：`https://github.com/zubair-trabzada/geo-seo-claude`
- 上游许可证：MIT License（MIT 许可证）
- 原版权声明：`Copyright (c) 2026 Zubair Trabzada`
- 本仓库维护者：`blindgodw-sys`
- 本仓库性质：基于上游开源代码的 Codex 原生改写版本，不是上游官方发布版本。

MIT License（MIT 许可证）允许使用、复制、修改、发布、分发、再授权和销售软件副本，
前提是保留版权声明和许可声明。为符合 GitHub 开源社区规范，本仓库已经：

- 保留根目录 `LICENSE` 中的原 MIT License（MIT 许可证）文本；
- 在 `README.md` 中明确标注上游项目来源；
- 明确声明本仓库是独立维护的 Codex 改写版本；
- 在本文档中记录主要改写内容、改写思路和验证方式；
- 避免把本仓库描述为上游作者的官方版本。

### 改写目标

改写目标是让原 Claude Code 技能包可以在 Codex 中按技能方式安装和运行，同时尽量保持
原 GEO（生成式引擎优化）和 SEO（搜索引擎优化）审计能力的一致性。

本次改写重点解决：

- Codex 技能发现与调用；
- Codex 安装路径；
- 通过命令适配器实现可重复执行；
- 安全更新流程；
- Markdown（标记语言）、HTML（超文本标记语言）和 PDF（便携式文档格式）报告生成；
- 中文报告输出规则。

本仓库不声明 Claude Code 和 Codex 的 LLM（大语言模型）运行机制完全相同。这里的等价目标是：
脚本、技能路由、生成文件、安装流程和命令工作流在 Codex 下实现功能等价。

### 主要改写列表

#### 1. Codex 技能入口

新增：

- `codex/geo/SKILL.md`
- `codex/geo-update/SKILL.md`

作用：为 Codex 提供技能入口，并把常用 `geo` 命令路由到统一命令适配器。

#### 2. Codex 一键安装脚本

新增：

- `codex-install.sh`

作用：

- 将主技能安装到 `~/.codex/skills/geo`；
- 将各个 `geo-*` 子技能安装到 `~/.codex/skills`；
- 在 `~/.codex/skills/geo/.venv` 下创建独立 Python（编程语言）虚拟环境；
- 把安装后的技能路径从 Claude Code 目录改写为 Codex 目录；
- 把 Python 脚本解释器固定到独立虚拟环境；
- 更新前把旧安装移动到 `/tmp` 下的带时间戳备份目录。

#### 3. 命令适配器

新增：

- `scripts/geo_cli.py`

作用：为 Codex 提供稳定、可重复执行的命令入口，包括：

- `audit`
- `quick`
- `citability`
- `crawlers`
- `llmstxt`
- `brands`
- `platforms`
- `schema`
- `technical`
- `content`
- `report`
- `report-pdf`
- `prospect`
- `proposal`
- `compare`
- `update`
- `full-test`

#### 4. 报告生成与中文支持

保留原 Markdown（标记语言）报告生成能力，并增加 Codex 下的 HTML（超文本标记语言）和
PDF（便携式文档格式）报告生成路径。

面向用户的报告规则已增加中文支持：报告内容默认可输出中文；如果必须使用英文技术名词，
首次出现时应补充中文括号说明，例如：

- `GEO（生成式引擎优化）`
- `Schema（结构化数据）`
- `PDF（便携式文档格式）`

#### 5. 更新流程

新增 Codex 安全更新路径：

- `geo-update`
- `geo_cli.py update`

更新流程保持保守：

- 替换文件前检查路径；
- 保留旧安装备份；
- 避免破坏性清理。

#### 6. 全量测试流程

新增：

- `geo_cli.py full-test <url>`

作用：验证技能包命令集合和预期输出文件是否能在 Codex 下完整运行。

全量测试用于验证技能包本身，不会写入外部生产 CRM（客户关系管理）系统，也不会修改目标网站。

### 本分支新增文件

- `codex-install.sh`
- `codex/geo/SKILL.md`
- `codex/geo-update/SKILL.md`
- `docs/codex-port-plan.md`
- `docs/codex-port-notes.md`
- `scripts/geo_cli.py`

### 已执行验证

发布前已执行的本地验证包括：

- `bash -n codex-install.sh`
- `python3 -m py_compile scripts/geo_cli.py`
- 验证公开安装脚本 URL 可访问：
  `https://raw.githubusercontent.com/blindgodw-sys/geo-seo-claude-codex/main/codex-install.sh`

Codex 改写版本也已经使用以下网站执行过完整技能调用验证：

- `https://www.lacewigsbuy.com`

验证结果显示命令和文件检查通过。生成的客户报告和测试目录不属于发布仓库内容。

### 公开安装命令

```bash
curl -fsSL https://raw.githubusercontent.com/blindgodw-sys/geo-seo-claude-codex/main/codex-install.sh | bash
```

### 非目标

本仓库不声明：

- 获得上游作者官方背书；
- Claude Code 和 Codex 的 LLM（大语言模型）推理行为完全一致；
- 测试流程会写入生产 CRM（客户关系管理）系统或修改目标网站。

---

# English Notes

This document explains how this repository was adapted from the upstream
`geo-seo-claude` project for Codex.

## Upstream Attribution

This project is based on the open-source repository:

- Upstream project: https://github.com/zubair-trabzada/geo-seo-claude
- Upstream license: MIT License
- Original copyright: Copyright (c) 2026 Zubair Trabzada

The original MIT License text is preserved in the root `LICENSE` file. This
fork is maintained independently by `blindgodw-sys` and is not an official
release of the upstream project.

## Compliance Notes

The upstream project uses the MIT License, which permits use, copying,
modification, publishing, distribution, sublicensing, and sale of copies, as
long as the copyright notice and permission notice are included in copies or
substantial portions of the software.

For that reason this fork:

- preserves the upstream `LICENSE` file;
- explicitly links to the upstream project in `README.md`;
- states that this is an independent Codex-native adaptation;
- documents the major modifications in this file;
- avoids presenting the fork as an official upstream release.

## Porting Goal

The goal was to make the original Claude Code skill bundle install and run as
a Codex skill bundle while keeping the original GEO and SEO audit behavior as
close as possible.

The port focuses on environment and workflow compatibility:

- Codex skill discovery and invocation;
- Codex installation paths;
- reproducible command execution through a CLI adapter;
- safe update workflow;
- report generation in Markdown, HTML, and PDF outputs.

LLM runtime behavior is not claimed to be identical across Claude Code and
Codex. The port targets functional equivalence for deterministic scripts,
skill routing, generated files, and command workflows.

## Major Changes

### Codex Skill Entrypoints

Added:

- `codex/geo/SKILL.md`
- `codex/geo-update/SKILL.md`

These files define the Codex-facing skill behavior and route common `geo`
commands to the command adapter.

### Codex Installer

Added:

- `codex-install.sh`

The installer:

- installs the main skill into `~/.codex/skills/geo`;
- installs focused `geo-*` sub-skills into `~/.codex/skills`;
- creates an isolated Python virtual environment under
  `~/.codex/skills/geo/.venv`;
- rewrites installed skill references from Claude Code paths to Codex paths;
- pins Python script shebangs to the isolated venv interpreter;
- preserves any previous installation by moving it to a timestamped backup
  under `/tmp`.

### Command Adapter

Added:

- `scripts/geo_cli.py`

The adapter provides repeatable commands for Codex usage, including:

- `audit`
- `quick`
- `citability`
- `crawlers`
- `llmstxt`
- `brands`
- `platforms`
- `schema`
- `technical`
- `content`
- `report`
- `report-pdf`
- `prospect`
- `proposal`
- `compare`
- `update`
- `full-test`

This gives Codex a stable script entrypoint instead of relying only on
Claude-style slash command routing.

### Report Generation

The port keeps Markdown report generation and adds Codex-oriented HTML/PDF
report generation paths through the CLI adapter.

User-facing report templates and summaries were updated so generated reports
can be produced in Chinese. When English technical terms are needed, the
reporting rules require a Chinese parenthetical explanation on first use.

Examples:

- `GEO（生成式引擎优化）`
- `Schema（结构化数据）`
- `PDF（便携式文档格式）`

### Update Workflow

Added a Codex-safe update path through `geo-update` and `geo_cli.py update`.
The workflow is intentionally conservative:

- it checks update paths before replacing files;
- it preserves prior installs through backups;
- it avoids destructive cleanup.

### Full-Test Workflow

Added `geo_cli.py full-test <url>` to validate the installed workflow across
the command set and expected output files.

The full-test workflow is intended to verify the skill bundle itself. It does
not write to external production CRM systems and does not modify the target
website.

## Web Access Differences

The original project referenced Claude Code web tooling. In Codex, the port
uses the following operating model:

- simple web retrieval can use Codex-compatible HTTP/web access;
- complex browser interaction can be handled with Playwright when available;
- deterministic Python scripts remain the preferred path for repeatable audit
  work.

## Files Added By This Fork

Primary added files:

- `codex-install.sh`
- `codex/geo/SKILL.md`
- `codex/geo-update/SKILL.md`
- `docs/codex-port-plan.md`
- `docs/codex-port-notes.md`
- `scripts/geo_cli.py`

The original upstream files remain present unless otherwise noted by normal
Git history.

## Validation Performed

Local validation before publication included:

- `bash -n codex-install.sh`
- `python3 -m py_compile scripts/geo_cli.py`
- verification that the published raw installer URL is reachable:
  `https://raw.githubusercontent.com/blindgodw-sys/geo-seo-claude-codex/main/codex-install.sh`

The Codex port was also previously exercised against:

- `https://www.lacewigsbuy.com`

That validation produced a full command/file pass in the local development
environment. Generated client reports and test run directories are not part of
the published repository.

## Public Installation Command

```bash
curl -fsSL https://raw.githubusercontent.com/blindgodw-sys/geo-seo-claude-codex/main/codex-install.sh | bash
```

## Non-Goals

This fork does not claim:

- official endorsement by the upstream author;
- identical LLM reasoning behavior across Claude Code and Codex;
- production writes to CRM systems or target websites during test runs.

Its scope is a Codex-native installation and execution path for the GEO/SEO
skill bundle.
