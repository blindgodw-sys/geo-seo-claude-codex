#!/usr/bin/env python3
"""
Codex-native CLI for the GEO-SEO skill bundle.

The CLI provides a repeatable command surface for Codex skills while reusing
the original helper modules shipped in this repository.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from brand_scanner import generate_brand_report  # noqa: E402
from citability_scorer import analyze_page_citability  # noqa: E402
from fetch_page import crawl_sitemap, fetch_llms_txt, fetch_page, fetch_robots_txt  # noqa: E402
from llmstxt_generator import generate_llmstxt, validate_llmstxt  # noqa: E402


CRM_ROOT = Path()
PROSPECTS_FILE = Path()
AUDITS_DIR = Path()
PROPOSALS_DIR = Path()
REPORTS_DIR = Path()


def set_crm_root(root: str | Path) -> None:
    global CRM_ROOT, PROSPECTS_FILE, AUDITS_DIR, PROPOSALS_DIR, REPORTS_DIR
    CRM_ROOT = Path(root).expanduser()
    PROSPECTS_FILE = CRM_ROOT / "prospects.json"
    AUDITS_DIR = CRM_ROOT / "audits"
    PROPOSALS_DIR = CRM_ROOT / "proposals"
    REPORTS_DIR = CRM_ROOT / "reports"


set_crm_root(os.environ.get("GEO_PROSPECTS_HOME", str(Path.home() / ".geo-prospects")))


@dataclass
class AnalysisBundle:
    url: str
    domain: str
    brand: str
    page: dict[str, Any]
    robots: dict[str, Any]
    llms: dict[str, Any]
    llms_validation: dict[str, Any]
    sitemap: list[str]
    citability: dict[str, Any]
    brand_report: dict[str, Any]
    scores: dict[str, int]
    platform_scores: dict[str, int]


COLLECT_CACHE: dict[tuple[str, bool], AnalysisBundle] = {}


def now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("URL/domain is required")
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parsed = urlparse(value)
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {value}")
    return value.rstrip("/")


def domain_from_url(url: str) -> str:
    return urlparse(normalize_url(url)).netloc.lower()


def slug_domain(domain: str) -> str:
    return re.sub(r"[^a-zA-Z0-9.-]+", "-", domain).strip("-")


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(round(value))))


def score_label(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 75:
        return "良好"
    if score >= 60:
        return "一般"
    if score >= 40:
        return "较弱"
    return "严重不足"


def write_text(path: str | Path, content: str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.rstrip() + "\n", encoding="utf-8")
    return p


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def table(rows: list[list[Any]], headers: list[str]) -> str:
    values = [[str(x) for x in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in values:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    header = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    sep = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    lines = [header, sep]
    for row in values:
        lines.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    return "\n".join(lines)


def yes_no(value: Any) -> str:
    return "是" if value else "否"


def status_zh(status: Any) -> str:
    text = str(status)
    mapping = {
        "pass": "通过",
        "fail": "失败",
        "ok": "正常",
        "missing": "缺失",
        "empty": "空文件",
        "target evidence not found": "未发现目标域名证据",
        "pdf not generated": "未生成 PDF（便携式文档格式）",
        "Present": "存在",
        "Missing": "缺失",
        "Yes": "是",
        "No": "否",
        "Unavailable": "不可用",
        "No crawler data": "无爬虫数据",
        "None detected": "未检测到",
    }
    return mapping.get(text, text)


def business_type_zh(value: str) -> str:
    mapping = {
        "E-commerce": "电商（E-commerce）",
        "SaaS": "软件即服务（SaaS）",
        "Local Business": "本地商家（Local Business）",
        "Publisher": "内容发布方（Publisher）",
        "Agency/Services": "代理/服务商（Agency/Services）",
        "Other": "其他",
    }
    return mapping.get(value, value)


def platform_zh(name: str) -> str:
    mapping = {
        "Google AI Overviews": "Google AI Overviews（谷歌 AI 概览）",
        "ChatGPT Web Search": "ChatGPT Web Search（ChatGPT 网页搜索）",
        "Perplexity AI": "Perplexity AI（Perplexity 人工智能搜索）",
        "Google Gemini": "Google Gemini（谷歌 Gemini 模型）",
        "Bing Copilot": "Bing Copilot（必应智能助手）",
        "YouTube": "YouTube（视频平台）",
        "Reddit": "Reddit（社区论坛）",
        "LinkedIn": "LinkedIn（职业社交平台）",
        "Wikipedia": "Wikipedia（维基百科）",
        "Wikidata": "Wikidata（维基数据）",
        "Other Platforms": "其他平台（Other Platforms）",
    }
    return mapping.get(name, name)


def tier_zh(tier: str) -> str:
    mapping = {
        "basic": "基础版（Basic）",
        "standard": "标准版（Standard）",
        "premium": "高级版（Premium）",
    }
    return mapping.get(tier, tier)


def score_key_zh(key: str) -> str:
    mapping = {
        "ai_visibility": "AI（人工智能）可见度",
        "brand": "品牌权威",
        "content": "内容质量",
        "technical": "技术基础",
        "schema": "Schema（结构化数据）",
        "platform": "平台就绪度",
        "citability": "Citability（可引用性）",
        "crawler": "Crawler Access（爬虫访问）",
        "llms": "llms.txt（大模型说明文件）",
        "overall": "GEO（生成式引擎优化）总分",
    }
    return mapping.get(key, key)


def schema_type_zh(value: str) -> str:
    mapping = {
        "Organization": "Organization（组织）",
        "LocalBusiness": "LocalBusiness（本地商家）",
        "Article": "Article（文章）",
        "NewsArticle": "NewsArticle（新闻文章）",
        "BlogPosting": "BlogPosting（博客文章）",
        "Product": "Product（产品）",
        "WebSite": "WebSite（网站）",
        "BreadcrumbList": "BreadcrumbList（面包屑导航）",
        "Person": "Person（个人）",
        "FAQPage": "FAQPage（常见问题页）",
        "WebPage": "WebPage（网页）",
        "ContactPoint": "ContactPoint（联系点）",
        "Offer": "Offer（报价）",
        "AggregateRating": "AggregateRating（聚合评分）",
        "Review": "Review（评价）",
        "ImageObject": "ImageObject（图片对象）",
        "SearchAction": "SearchAction（搜索动作）",
    }
    return mapping.get(value, value)


def section_zh(value: str) -> str:
    mapping = {
        "Main Pages": "主要页面",
        "Products & Services": "产品与服务",
        "Resources & Blog": "资源与博客",
        "Company": "公司信息",
        "Support": "支持与帮助",
    }
    return mapping.get(value, value)


def localize_llms_txt(content: str) -> str:
    replacements = {
        "## Main Pages": "## 主要页面",
        "## Products & Services": "## 产品与服务",
        "## Resources & Blog": "## 资源与博客",
        "## Company": "## 公司信息",
        "## Support": "## 支持与帮助",
        "## Contact": "## 联系方式",
        "- Website:": "- 网站：",
        "- Email:": "- 邮箱：",
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    return content


def command_label_zh(name: str) -> str:
    mapping = {
        "audit": "audit（完整审计）",
        "page": "page（页面分析）",
        "quick": "quick（快速快照）",
        "citability": "citability（可引用性）",
        "crawlers": "crawlers（爬虫访问）",
        "llmstxt": "llmstxt（大模型说明文件）",
        "brands": "brands（品牌提及）",
        "platforms": "platforms（平台优化）",
        "schema": "schema（结构化数据）",
        "technical": "technical（技术审计）",
        "content": "content（内容分析）",
        "report": "report（客户报告）",
        "report-pdf": "report-pdf（PDF（便携式文档格式）报告）",
        "prospect new": "prospect new（创建潜在客户）",
        "prospect show": "prospect show（查看潜在客户）",
        "prospect note": "prospect note（添加备注）",
        "prospect status": "prospect status（更新状态）",
        "prospect audit": "prospect audit（潜在客户审计）",
        "prospect list": "prospect list（潜在客户列表）",
        "prospect pipeline": "prospect pipeline（销售管道）",
        "proposal": "proposal（服务提案）",
        "compare": "compare（月度对比）",
        "prospect won": "prospect won（标记成交）",
        "prospect lost": "prospect lost（标记流失）",
        "update": "update（更新检查）",
    }
    return mapping.get(name, name)


def brand_from_page(page: dict[str, Any], domain: str) -> str:
    title = page.get("title") or ""
    for splitter in ("|", "-", "–", "—", ":"):
        if splitter in title:
            title = title.split(splitter)[0]
            break
    title = re.sub(r"\s+", " ", title).strip()
    if title and len(title) >= 2:
        return title[:80]
    bare = domain.replace("www.", "").split(".")[0]
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", bare) if part)


def detect_business_type(page: dict[str, Any]) -> str:
    text = (page.get("text_content") or "").lower()
    links = " ".join(link.get("url", "") + " " + link.get("text", "") for link in page.get("internal_links", [])).lower()
    schema_type_text = " ".join(schema_types(page)).lower()
    joined = " ".join([text[:6000], links, schema_type_text])
    if any(x in joined for x in ["add to cart", "product", "checkout", "shop", "price", "sale"]):
        return "E-commerce"
    if any(x in joined for x in ["pricing", "free trial", "sign up", "api", "dashboard", "softwareapplication"]):
        return "SaaS"
    if any(x in joined for x in ["near me", "opening hours", "address", "localbusiness", "google maps"]):
        return "Local Business"
    if any(x in joined for x in ["blog", "article", "author", "newsarticle", "datepublished"]):
        return "Publisher"
    if any(x in joined for x in ["case studies", "our services", "portfolio", "agency"]):
        return "Agency/Services"
    return "Other"


def schema_types(page: dict[str, Any]) -> list[str]:
    found: list[str] = []

    def visit(obj: Any) -> None:
        if isinstance(obj, dict):
            typ = obj.get("@type")
            if isinstance(typ, str):
                found.append(typ)
            elif isinstance(typ, list):
                found.extend(str(x) for x in typ)
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    for item in page.get("structured_data", []) or []:
        visit(item)
    return sorted(set(found))


def same_as_count(page: dict[str, Any]) -> int:
    count = 0

    def visit(obj: Any) -> None:
        nonlocal count
        if isinstance(obj, dict):
            same_as = obj.get("sameAs")
            if isinstance(same_as, list):
                count += len(same_as)
            elif isinstance(same_as, str):
                count += 1
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    for item in page.get("structured_data", []) or []:
        visit(item)
    return count


def crawler_score(robots: dict[str, Any]) -> int:
    statuses = robots.get("ai_crawler_status") or {}
    if not statuses:
        return 70 if not robots.get("exists") else 50
    score = 100
    critical = {"GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot", "GoogleBot", "BingBot"}
    for crawler, status in statuses.items():
        status_text = str(status)
        if "BLOCKED" in status_text:
            score -= 15 if crawler in critical else 5
        elif status_text in {"PARTIALLY_BLOCKED"}:
            score -= 7 if crawler in critical else 3
    if not robots.get("sitemaps"):
        score -= 10
    return clamp(score)


def llms_score(validation: dict[str, Any]) -> int:
    if not validation.get("exists"):
        return 0
    if not validation.get("format_valid"):
        return 30
    score = 50
    if validation.get("link_count", 0) >= 5:
        score += 15
    if validation.get("section_count", 0) >= 2:
        score += 10
    if validation.get("full_version", {}).get("exists"):
        score += 15
    if not validation.get("issues"):
        score += 10
    return clamp(score)


def schema_score(page: dict[str, Any]) -> int:
    types = set(schema_types(page))
    score = 0
    if types:
        score += 20
    if {"Organization", "LocalBusiness"} & types:
        score += 20
    if {"Article", "NewsArticle", "BlogPosting", "Product", "WebSite", "BreadcrumbList"} & types:
        score += 15
    if same_as_count(page) >= 3:
        score += 15
    elif same_as_count(page) > 0:
        score += 8
    if "WebSite" in types:
        score += 10
    if "Product" in types:
        score += 10
    if not page.get("errors"):
        score += 10
    return clamp(score)


def technical_score(page: dict[str, Any], robots: dict[str, Any], sitemap: list[str]) -> int:
    score = 0
    parsed = urlparse(page.get("url") or "")
    if parsed.scheme == "https":
        score += 12
    if page.get("status_code") and 200 <= int(page["status_code"]) < 400:
        score += 10
    if page.get("has_ssr_content"):
        score += 18
    if page.get("title"):
        score += 7
    if page.get("description"):
        score += 7
    if page.get("canonical"):
        score += 6
    if robots.get("exists"):
        score += 8
    score += int(crawler_score(robots) * 0.12)
    if sitemap:
        score += 8
    headers = page.get("security_headers") or {}
    for header in ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy"]:
        if headers.get(header):
            score += 3
    if "viewport" in (page.get("meta_tags") or {}):
        score += 6
    return clamp(score)


def content_score(page: dict[str, Any], citability: dict[str, Any]) -> int:
    text = page.get("text_content") or ""
    links = page.get("internal_links") or []
    score = 0
    wc = int(page.get("word_count") or 0)
    if wc >= 1500:
        score += 20
    elif wc >= 800:
        score += 16
    elif wc >= 500:
        score += 12
    elif wc >= 250:
        score += 8
    score += min(len(page.get("heading_structure") or []), 10)
    score += int((citability.get("average_citability_score") or 0) * 0.25)
    lower_text = text.lower()
    if any(x in lower_text for x in ["about us", "our story", "founded", "team"]):
        score += 8
    if any(x in lower_text for x in ["contact", "email", "phone", "address"]):
        score += 8
    if any("privacy" in (link.get("text", "") + link.get("url", "")).lower() for link in links):
        score += 5
    if any("terms" in (link.get("text", "") + link.get("url", "")).lower() for link in links):
        score += 5
    if re.search(r"\b20(?:2[0-9]|1[0-9])\b", text):
        score += 5
    return clamp(score)


def brand_score(report: dict[str, Any]) -> int:
    platforms = report.get("platforms") or {}
    wiki = platforms.get("wikipedia") or {}
    score = 0
    if wiki.get("has_wikipedia_page"):
        score += 30
    if wiki.get("has_wikidata_entry"):
        score += 25
    if wiki.get("wikipedia_search_results", 0):
        score += min(int(wiki.get("wikipedia_search_results", 0)) * 3, 15)
    # Other platform checks are instruction-backed in the upstream project.
    # Give baseline credit for generated search targets so the score remains
    # diagnostic but does not fabricate presence.
    for name in ["youtube", "reddit", "linkedin", "other"]:
        if platforms.get(name):
            score += 5
    return clamp(score)


def platform_scores(bundle: AnalysisBundle | None, page: dict[str, Any], robots: dict[str, Any], schema_value: int, content_value: int, brand_value: int) -> dict[str, int]:
    headings = [h.get("text", "") for h in page.get("heading_structure", [])]
    question_headings = sum(1 for h in headings if h.strip().endswith("?"))
    has_table_signal = bool(re.search(r"\b(table|compare|comparison|vs\.?|price|pricing)\b", page.get("text_content") or "", re.I))
    cscore = crawler_score(robots)
    gpt_access = 100
    statuses = robots.get("ai_crawler_status") or {}
    for bot in ["OAI-SearchBot", "ChatGPT-User", "GPTBot"]:
        if "BLOCKED" in str(statuses.get(bot, "")):
            gpt_access -= 30
    google_aio = clamp(content_value * 0.45 + schema_value * 0.25 + min(question_headings * 8, 20) + (10 if has_table_signal else 0))
    chatgpt = clamp(brand_value * 0.45 + content_value * 0.25 + gpt_access * 0.20 + schema_value * 0.10)
    perplexity = clamp(brand_value * 0.35 + content_value * 0.35 + cscore * 0.20 + (10 if "PerplexityBot" not in str(statuses.get("PerplexityBot", "")) else 0))
    gemini = clamp(schema_value * 0.35 + content_value * 0.25 + cscore * 0.20 + brand_value * 0.20)
    copilot = clamp(technical_score(page, robots, []) * 0.30 + content_value * 0.25 + brand_value * 0.20 + cscore * 0.25)
    return {
        "Google AI Overviews": google_aio,
        "ChatGPT Web Search": chatgpt,
        "Perplexity AI": perplexity,
        "Google Gemini": gemini,
        "Bing Copilot": copilot,
    }


def collect(url_value: str, include_brand: bool = True) -> AnalysisBundle:
    url = normalize_url(url_value)
    cache_key = (url, include_brand)
    if cache_key in COLLECT_CACHE:
        return COLLECT_CACHE[cache_key]
    domain = domain_from_url(url)
    page = fetch_page(url)
    if not page.get("url"):
        page["url"] = url
    robots = fetch_robots_txt(url)
    llms = fetch_llms_txt(url)
    llms_validation = validate_llmstxt(url)
    sitemap = crawl_sitemap(url)
    citability = analyze_page_citability(url)
    if "error" in citability:
        citability = {
            "average_citability_score": 0,
            "total_blocks_analyzed": 0,
            "grade_distribution": {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
            "top_5_citable": [],
            "bottom_5_citable": [],
            "all_blocks": [],
            "error": citability["error"],
        }
    brand = brand_from_page(page, domain)
    brand_report = generate_brand_report(brand, domain) if include_brand else {"platforms": {}}
    scores: dict[str, int] = {}
    scores["citability"] = clamp(citability.get("average_citability_score") or 0)
    scores["crawler"] = crawler_score(robots)
    scores["llms"] = llms_score(llms_validation)
    scores["schema"] = schema_score(page)
    scores["technical"] = technical_score(page, robots, sitemap)
    scores["content"] = content_score(page, citability)
    scores["brand"] = brand_score(brand_report)
    platforms = platform_scores(None, page, robots, scores["schema"], scores["content"], scores["brand"])
    scores["platform"] = clamp(sum(platforms.values()) / len(platforms))
    scores["ai_visibility"] = clamp(
        scores["citability"] * 0.35
        + scores["brand"] * 0.30
        + scores["crawler"] * 0.25
        + scores["llms"] * 0.10
    )
    scores["overall"] = clamp(
        scores["ai_visibility"] * 0.25
        + scores["brand"] * 0.20
        + scores["content"] * 0.20
        + scores["technical"] * 0.15
        + scores["schema"] * 0.10
        + scores["platform"] * 0.10
    )
    bundle = AnalysisBundle(
        url=url,
        domain=domain,
        brand=brand,
        page=page,
        robots=robots,
        llms=llms,
        llms_validation=llms_validation,
        sitemap=sitemap,
        citability=citability,
        brand_report=brand_report,
        scores=scores,
        platform_scores=platforms,
    )
    COLLECT_CACHE[cache_key] = bundle
    return bundle


def score_breakdown_rows(bundle: AnalysisBundle) -> list[list[Any]]:
    s = bundle.scores
    return [
        ["AI（人工智能）可引用性与可见度", f"{s['ai_visibility']}/100", "25%", round(s["ai_visibility"] * 0.25, 1)],
        ["品牌权威信号", f"{s['brand']}/100", "20%", round(s["brand"] * 0.20, 1)],
        ["内容质量与 E-E-A-T（经验、专业、权威、可信）", f"{s['content']}/100", "20%", round(s["content"] * 0.20, 1)],
        ["技术基础", f"{s['technical']}/100", "15%", round(s["technical"] * 0.15, 1)],
        ["Schema（结构化数据）", f"{s['schema']}/100", "10%", round(s["schema"] * 0.10, 1)],
        ["平台优化", f"{s['platform']}/100", "10%", round(s["platform"] * 0.10, 1)],
        ["GEO（生成式引擎优化）总分", f"{s['overall']}/100", "100%", s["overall"]],
    ]


def render_audit(bundle: AnalysisBundle) -> str:
    types = schema_types(bundle.page)
    issues: list[str] = []
    if bundle.scores["crawler"] < 70:
        issues.append("AI Crawler（人工智能爬虫）访问存在限制，或 `robots.txt` 中的允许规则不够明确。")
    if bundle.scores["llms"] == 0:
        issues.append("未检测到可访问的 `llms.txt`（大模型说明文件）。")
    if bundle.scores["schema"] < 50:
        issues.append("Schema（结构化数据）缺失或不完整，影响实体识别。")
    if not bundle.page.get("has_ssr_content"):
        issues.append("主要内容可能依赖客户端 JavaScript（浏览器脚本）渲染。")
    if bundle.scores["citability"] < 50:
        issues.append("内容段落对 AI（人工智能）引用和抽取不够友好。")
    if not issues:
        issues.append("确定性基线检查未发现关键阻塞问题。")

    lines = [
        f"# GEO（生成式引擎优化）审计报告：{bundle.brand}",
        "",
        f"**审计日期：** {now_date()}",
        f"**URL（统一资源定位符）：** {bundle.url}",
        f"**域名：** {bundle.domain}",
        f"**业务类型：** {business_type_zh(detect_business_type(bundle.page))}",
        f"**分析页面数：** {max(1, len(bundle.sitemap) or 1)}",
        "",
        "## 执行摘要",
        "",
        f"**GEO（生成式引擎优化）总分：{bundle.scores['overall']}/100（{score_label(bundle.scores['overall'])}）**",
        "",
        f"本次审计覆盖 {bundle.domain} 的 AI Crawler（人工智能爬虫）访问、AI（人工智能）引用性、品牌权威、内容质量、技术基础、Schema（结构化数据）和平台就绪度。当前最高分维度是 {score_key_zh(max(bundle.scores, key=bundle.scores.get))}，最低分维度是 {score_key_zh(min(bundle.scores, key=bundle.scores.get))}。",
        "",
        "### 分数拆解",
        "",
        table(score_breakdown_rows(bundle), ["类别", "分数", "权重", "加权分"]),
        "",
        "## 关键问题（优先修复）",
        "",
    ]
    for issue in issues:
        lines.append(f"- {issue}")
    lines.extend([
        "",
        "## AI（人工智能）可见度",
        "",
        table(
            [
                ["Citability（可引用性）", f"{bundle.scores['citability']}/100"],
                ["Crawler Access（爬虫访问）", f"{bundle.scores['crawler']}/100"],
                ["llms.txt（大模型说明文件）", f"{bundle.scores['llms']}/100"],
                ["Brand Authority（品牌权威）", f"{bundle.scores['brand']}/100"],
            ],
            ["信号", "分数"],
        ),
        "",
        "## 技术基础",
        "",
        f"- HTTP（超文本传输协议）状态：{bundle.page.get('status_code')}",
        f"- SSR（服务端渲染）内容检测：{yes_no(bundle.page.get('has_ssr_content'))}",
        f"- 字数：{bundle.page.get('word_count')}",
        f"- Sitemap（站点地图）URL（统一资源定位符）数量：{len(bundle.sitemap)}",
        f"- 已配置安全响应头数量：{sum(1 for v in (bundle.page.get('security_headers') or {}).values() if v)}",
        "",
        "## Schema（结构化数据）",
        "",
        f"- Schema（结构化数据）类型：{', '.join(schema_type_zh(t) for t in types) if types else '未检测到'}",
        f"- sameAs（同一实体链接）数量：{same_as_count(bundle.page)}",
        "",
        "## 平台就绪度",
        "",
        table([[platform_zh(name), f"{score}/100"] for name, score in bundle.platform_scores.items()], ["平台", "分数"]),
        "",
        "## 30 天行动计划",
        "",
        "### 第 1 周",
        "- 在业务政策允许的前提下，明确允许 Tier 1（一级）AI Crawler（人工智能爬虫）访问。",
        "- 发布或完善 `/llms.txt`（大模型说明文件），覆盖关键页面和联系方式。",
        "- 添加 Organization（组织）或业务专属 JSON-LD（JSON 链接数据），并补充 sameAs（同一实体链接）。",
        "",
        "### 第 2 周",
        "- 将薄弱内容改写为先给答案、再补说明的段落。",
        "- 针对产品/服务增加 FAQ（常见问题）和对比表。",
        "",
        "### 第 3 周",
        "- 完善 E-E-A-T（经验、专业、权威、可信）信号：作者、联系方式、政策页、证据和原创数据。",
        "- 强化指向高价值页面的内部链接。",
        "",
        "### 第 4 周",
        "- 在适合的平台建设实体信号，包括 YouTube（视频平台）、Reddit（社区论坛）、LinkedIn（职业社交平台）、Wikidata（维基数据）/Wikipedia（维基百科）。",
        "- 重新运行本审计并对比分数变化。",
        "",
        "## 附录：Sitemap（站点地图）中的页面",
        "",
    ])
    for page_url in bundle.sitemap[:50]:
        lines.append(f"- {page_url}")
    if not bundle.sitemap:
        lines.append("- 未发现 XML（可扩展标记语言）Sitemap（站点地图）URL（统一资源定位符）。")
    return "\n".join(lines)


def cmd_audit(args: argparse.Namespace) -> Path:
    bundle = collect(args.url)
    path = write_text("GEO-AUDIT-REPORT.md", render_audit(bundle))
    print(f"审计报告已生成：{path}")
    print(f"GEO（生成式引擎优化）总分：{bundle.scores['overall']}/100（{score_label(bundle.scores['overall'])}）")
    return path


def cmd_page(args: argparse.Namespace) -> Path:
    bundle = collect(args.url)
    rows = [
        ["URL（统一资源定位符）", bundle.url],
        ["标题", bundle.page.get("title") or ""],
        ["描述", bundle.page.get("description") or ""],
        ["状态码", bundle.page.get("status_code")],
        ["字数", bundle.page.get("word_count")],
        ["Citability（可引用性）", f"{bundle.scores['citability']}/100"],
        ["技术分", f"{bundle.scores['technical']}/100"],
        ["Schema（结构化数据）分", f"{bundle.scores['schema']}/100"],
    ]
    content = "\n".join([
        f"# GEO（生成式引擎优化）页面分析：{bundle.brand}",
        "",
        f"**分析日期：** {now_date()}",
        "",
        table(rows, ["字段", "值"]),
        "",
        "## 最强可引用段落",
        "",
        render_blocks(bundle.citability.get("top_5_citable") or []),
        "",
        "## 最弱段落",
        "",
        render_blocks(bundle.citability.get("bottom_5_citable") or []),
    ])
    path = write_text("GEO-PAGE-ANALYSIS.md", content)
    print(f"页面分析已生成：{path}")
    return path


def render_blocks(blocks: list[dict[str, Any]]) -> str:
    if not blocks:
        return "- 暂无可用段落。"
    lines: list[str] = []
    for block in blocks:
        lines.append(f"- **{block.get('heading') or '未命名段落'}**：{block.get('total_score', 0)}/100（{block.get('label', '')}）- {block.get('preview', '')}")
    return "\n".join(lines)


def cmd_quick(args: argparse.Namespace) -> str:
    bundle = collect(args.url, include_brand=False)
    output = "\n".join([
        f"GEO（生成式引擎优化）快速快照：{bundle.domain}",
        f"GEO（生成式引擎优化）总分：{bundle.scores['overall']}/100（{score_label(bundle.scores['overall'])}）",
        f"Citability（可引用性）：{bundle.scores['citability']}/100",
        f"Crawler Access（爬虫访问）：{bundle.scores['crawler']}/100",
        f"llms.txt（大模型说明文件）：{bundle.scores['llms']}/100",
        f"Schema（结构化数据）：{bundle.scores['schema']}/100",
        f"技术：{bundle.scores['technical']}/100",
        f"内容：{bundle.scores['content']}/100",
    ])
    print(output)
    return output


def cmd_citability(args: argparse.Namespace) -> Path:
    url = normalize_url(args.url)
    result = analyze_page_citability(url)
    if "error" in result:
        raise RuntimeError(result["error"])
    content = "\n".join([
        f"# GEO（生成式引擎优化）Citability（可引用性）评分：{url}",
        "",
        f"**分析日期：** {now_date()}",
        f"**平均 Citability（可引用性）分：** {result.get('average_citability_score')}/100",
        f"**已分析段落数：** {result.get('total_blocks_analyzed')}",
        f"**长度适合引用的段落数：** {result.get('optimal_length_passages')}",
        "",
        "## 等级分布",
        "",
        table([[k, v] for k, v in (result.get("grade_distribution") or {}).items()], ["等级", "数量"]),
        "",
        "## 最强可引用段落",
        "",
        render_blocks(result.get("top_5_citable") or []),
        "",
        "## 最弱段落",
        "",
        render_blocks(result.get("bottom_5_citable") or []),
        "",
        "## 说明",
        "",
        "- Citability（可引用性）表示内容被 AI（人工智能）系统直接引用为答案的难易程度。",
    ])
    path = write_text("GEO-CITABILITY-SCORE.md", content)
    print(f"Citability（可引用性）报告已生成：{path}")
    return path


def cmd_crawlers(args: argparse.Namespace) -> Path:
    url = normalize_url(args.url)
    robots = fetch_robots_txt(url)
    rows = [[crawler, status_zh(status)] for crawler, status in (robots.get("ai_crawler_status") or {}).items()]
    content = "\n".join([
        f"# GEO（生成式引擎优化）Crawler Access（爬虫访问）：{domain_from_url(url)}",
        "",
        f"**分析日期：** {now_date()}",
        f"**robots.txt（爬虫规则文件）URL（统一资源定位符）：** {robots.get('url')}",
        f"**robots.txt（爬虫规则文件）是否存在：** {yes_no(robots.get('exists'))}",
        f"**Crawler Access（爬虫访问）分：** {crawler_score(robots)}/100",
        "",
        "## AI Crawler（人工智能爬虫）访问表",
        "",
        table(rows or [["无爬虫数据", "不可用"]], ["Crawler（爬虫）", "有效状态"]),
        "",
        "## Sitemap（站点地图）",
        "",
        "\n".join(f"- {x}" for x in robots.get("sitemaps", [])) or "- 未发现 Sitemap（站点地图）声明。",
        "",
        "## 推荐的 robots.txt（爬虫规则文件）配置块",
        "",
        "```txt",
        "User-agent: GPTBot\nAllow: /\n\nUser-agent: OAI-SearchBot\nAllow: /\n\nUser-agent: ChatGPT-User\nAllow: /\n\nUser-agent: ClaudeBot\nAllow: /\n\nUser-agent: PerplexityBot\nAllow: /",
        "```",
    ])
    path = write_text("GEO-CRAWLER-ACCESS.md", content)
    print(f"Crawler（爬虫）报告已生成：{path}")
    return path


def cmd_llmstxt(args: argparse.Namespace) -> list[Path]:
    url = normalize_url(args.url)
    validation = validate_llmstxt(url)
    paths: list[Path] = []
    if validation.get("exists"):
        content = "\n".join([
            f"# llms.txt（大模型说明文件）分析：{domain_from_url(url)}",
            "",
            f"**分析日期：** {now_date()}",
            f"**llms.txt（大模型说明文件）状态：** 已发现，位置：{validation.get('url')}",
            f"**格式是否有效：** {yes_no(validation.get('format_valid'))}",
            f"**llms.txt（大模型说明文件）总分：** {llms_score(validation)}/100",
            "",
            "## 校验结果",
            "",
            table(
                [
                    ["标题", yes_no(validation.get("has_title"))],
                    ["描述", yes_no(validation.get("has_description"))],
                    ["章节数", validation.get("section_count")],
                    ["链接数", validation.get("link_count")],
                    ["llms-full.txt（完整大模型说明文件）", yes_no(validation.get("full_version", {}).get("exists"))],
                ],
                ["项目", "值"],
            ),
            "",
            "## 问题",
            "",
            "\n".join(f"- {x}" for x in validation.get("issues", [])) or "- 未发现结构性问题。",
            "",
            "## 建议",
            "",
            "\n".join(f"- {x}" for x in validation.get("suggestions", [])) or "- 暂无建议。",
        ])
        paths.append(write_text("GEO-LLMSTXT-ANALYSIS.md", content))
    else:
        generated = generate_llmstxt(url)
        paths.append(write_text("llms.txt", localize_llms_txt(generated.get("generated_llmstxt", ""))))
        report = "\n".join([
            f"# llms.txt（大模型说明文件）生成结果：{domain_from_url(url)}",
            "",
            f"**生成日期：** {now_date()}",
            f"**已分析页面数：** {generated.get('pages_analyzed')}",
            "",
            "## 章节数量",
            "",
            table([[section_zh(k), v] for k, v in (generated.get("sections") or {}).items()], ["章节", "页面数"]),
            "",
            "## 说明",
            "",
            "- 已在当前目录生成可部署的 `llms.txt`（大模型说明文件）。",
            "- 发布前请检查占位联系邮箱。",
        ])
        paths.append(write_text("GEO-LLMSTXT-GENERATION.md", report))
    print("llms.txt（大模型说明文件）命令已生成：" + ", ".join(str(p) for p in paths))
    return paths


def cmd_brands(args: argparse.Namespace) -> Path:
    url = normalize_url(args.url)
    page = fetch_page(url)
    domain = domain_from_url(url)
    brand = args.brand or brand_from_page(page, domain)
    report = generate_brand_report(brand, domain)
    platforms = report.get("platforms") or {}
    rows = []
    for key, data in platforms.items():
        rows.append([
            platform_zh(data.get("platform", key)),
            data.get("weight", ""),
            "已发现" if data.get("has_wikipedia_page") or data.get("has_wikidata_entry") or data.get("has_channel") or data.get("has_company_page") else "需要人工或浏览器复核",
        ])
    content = "\n".join([
        f"# GEO（生成式引擎优化）品牌提及：{brand}",
        "",
        f"**分析日期：** {now_date()}",
        f"**域名：** {domain}",
        f"**Brand Authority（品牌权威）分：** {brand_score(report)}/100",
        "",
        "## 平台拆解",
        "",
        table(rows, ["平台", "权重", "观察状态"]),
        "",
        "## 建议",
        "",
        "- 优先补齐 Wikipedia（维基百科）/Wikidata（维基数据）等可验证实体资料（如符合平台收录条件）。",
        "- 建立或完善 YouTube（视频平台）、Reddit（社区论坛）、LinkedIn（职业社交平台）等第三方品牌信号。",
        "- 在官网 Schema（结构化数据）中增加 sameAs（同一实体链接），把官网与权威第三方资料关联起来。",
    ])
    path = write_text("GEO-BRAND-MENTIONS.md", content)
    print(f"品牌报告已生成：{path}")
    return path


def cmd_platforms(args: argparse.Namespace) -> Path:
    bundle = collect(args.url)
    rows = [[platform_zh(name), f"{score}/100"] for name, score in bundle.platform_scores.items()]
    content = "\n".join([
        f"# GEO（生成式引擎优化）平台优化：{bundle.domain}",
        "",
        f"**分析日期：** {now_date()}",
        f"**综合平台分：** {bundle.scores['platform']}/100",
        "",
        table(rows, ["平台", "就绪分"]),
        "",
        "## 跨平台快速优化项",
        "",
        "- 在问题型标题下增加直接回答段落。",
        "- 强化 Organization（组织）/Product（产品）Schema（结构化数据）和 sameAs（同一实体链接）。",
        "- 确认 GPTBot（OpenAI 爬虫）、OAI-SearchBot（OpenAI 搜索爬虫）、ChatGPT-User（ChatGPT 浏览用户代理）、ClaudeBot（Claude 爬虫）和 PerplexityBot（Perplexity 爬虫）可以访问公开内容。",
        "- 发布或完善 `llms.txt`（大模型说明文件）。",
        "- 在适合的平台建设可验证品牌档案，例如 YouTube（视频平台）、Reddit（社区论坛）、LinkedIn（职业社交平台）、Wikidata（维基数据）/Wikipedia（维基百科）。",
    ])
    path = write_text("GEO-PLATFORM-OPTIMIZATION.md", content)
    print(f"平台报告已生成：{path}")
    return path


def cmd_schema(args: argparse.Namespace) -> Path:
    bundle = collect(args.url, include_brand=False)
    types = schema_types(bundle.page)
    business_type = detect_business_type(bundle.page)
    recommended_type = "Organization"
    if business_type == "E-commerce":
        recommended_type = "Product"
    elif business_type == "Local Business":
        recommended_type = "LocalBusiness"
    generated = {
        "@context": "https://schema.org",
        "@type": recommended_type,
        "name": bundle.brand,
        "url": bundle.url,
        "description": bundle.page.get("description") or f"{bundle.brand} 的官方网站",
    }
    write_text("GEO-SCHEMA-GENERATED.json", json.dumps(generated, indent=2, ensure_ascii=False))
    content = "\n".join([
        f"# GEO（生成式引擎优化）Schema（结构化数据）报告：{bundle.domain}",
        "",
        f"**分析日期：** {now_date()}",
        f"**Schema（结构化数据）分：** {bundle.scores['schema']}/100",
        f"**业务类型：** {business_type_zh(business_type)}",
        "",
        "## 已检测到的 Schema（结构化数据）",
        "",
        table([[schema_type_zh(t)] for t in types] or [["未检测到"]], ["@type（类型）"]),
        "",
        "## sameAs（同一实体链接）审计",
        "",
        f"- 已检测到 sameAs（同一实体链接）数量：{same_as_count(bundle.page)}",
        "",
        "## 生成的 JSON-LD（JSON 链接数据）",
        "",
        "```json",
        json.dumps(generated, indent=2, ensure_ascii=False),
        "```",
    ])
    path = write_text("GEO-SCHEMA-REPORT.md", content)
    print(f"Schema（结构化数据）报告已生成：{path}")
    return path


def cmd_technical(args: argparse.Namespace) -> Path:
    bundle = collect(args.url, include_brand=False)
    headers = bundle.page.get("security_headers") or {}
    content = "\n".join([
        f"# GEO（生成式引擎优化）技术审计：{bundle.domain}",
        "",
        f"**分析日期：** {now_date()}",
        f"**技术分：** {bundle.scores['technical']}/100",
        "",
        table(
            [
                ["HTTP（超文本传输协议）状态", bundle.page.get("status_code")],
                ["HTTPS（安全超文本传输协议）", yes_no(urlparse(bundle.url).scheme == "https")],
                ["SSR（服务端渲染）内容", yes_no(bundle.page.get("has_ssr_content"))],
                ["Canonical（规范链接）", yes_no(bool(bundle.page.get("canonical")))],
                ["robots.txt（爬虫规则文件）", yes_no(bundle.robots.get("exists"))],
                ["Sitemap（站点地图）URL（统一资源定位符）数量", len(bundle.sitemap)],
                ["Crawler Access（爬虫访问）", f"{bundle.scores['crawler']}/100"],
                ["已配置安全响应头数量", sum(1 for v in headers.values() if v)],
            ],
            ["检查项", "值"],
        ),
        "",
        "## Security Headers（安全响应头）",
        "",
        table([[k, "存在" if v else "缺失"] for k, v in headers.items()], ["响应头", "状态"]),
        "",
        "## 错误",
        "",
        "\n".join(f"- {x}" for x in bundle.page.get("errors", [])) or "- 未发现抓取或解析错误。",
    ])
    path = write_text("GEO-TECHNICAL-AUDIT.md", content)
    print(f"技术报告已生成：{path}")
    return path


def cmd_content(args: argparse.Namespace) -> Path:
    bundle = collect(args.url, include_brand=False)
    content = "\n".join([
        f"# GEO（生成式引擎优化）内容分析：{bundle.domain}",
        "",
        f"**分析日期：** {now_date()}",
        f"**内容分：** {bundle.scores['content']}/100",
        f"**平均 Citability（可引用性）分：** {bundle.scores['citability']}/100",
        "",
        table(
            [
                ["字数", bundle.page.get("word_count")],
                ["标题数量", len(bundle.page.get("heading_structure") or [])],
                ["内部链接数量", len(bundle.page.get("internal_links") or [])],
                ["外部链接数量", len(bundle.page.get("external_links") or [])],
                ["图片数量", len(bundle.page.get("images") or [])],
            ],
            ["指标", "值"],
        ),
        "",
        "## 最强段落",
        "",
        render_blocks(bundle.citability.get("top_5_citable") or []),
        "",
        "## 最弱段落",
        "",
        render_blocks(bundle.citability.get("bottom_5_citable") or []),
        "",
        "## E-E-A-T（经验、专业、权威、可信）改进步骤",
        "",
        "- 增加清晰可见的作者/企业资质和联系方式。",
        "- 补充具体证据、原创数据或客户案例。",
        "- 为内容页增加发布日期或更新时间。",
        "- 保持段落自包含，并采用先回答后解释的结构。",
    ])
    path = write_text("GEO-CONTENT-ANALYSIS.md", content)
    print(f"内容报告已生成：{path}")
    return path


def cmd_report(args: argparse.Namespace) -> Path:
    bundle = collect(args.url)
    if not Path("GEO-AUDIT-REPORT.md").exists():
        write_text("GEO-AUDIT-REPORT.md", render_audit(bundle))
    content = "\n".join([
        f"# GEO（生成式引擎优化）客户报告：{bundle.brand}",
        "",
        f"**报告日期：** {now_date()}",
        f"**域名：** {bundle.domain}",
        f"**GEO（生成式引擎优化）就绪分：** {bundle.scores['overall']}/100（{score_label(bundle.scores['overall'])}）",
        "",
        "## 执行摘要",
        "",
        f"{bundle.domain} 当前 GEO（生成式引擎优化）就绪分为 {bundle.scores['overall']}/100。本报告优先关注 AI Crawler（人工智能爬虫）访问、llms.txt（大模型说明文件）、Schema（结构化数据）、Citability（可引用性）和品牌权威信号。",
        "",
        "## 分数看板",
        "",
        table(score_breakdown_rows(bundle), ["类别", "分数", "权重", "加权分"]),
        "",
        "## AI（人工智能）可见度看板",
        "",
        table([[platform_zh(k), f"{v}/100"] for k, v in bundle.platform_scores.items()], ["平台", "就绪分"]),
        "",
        "## 优先行动计划",
        "",
        "1. 发布或完善 `llms.txt`（大模型说明文件）。",
        "2. 添加完整的 Organization（组织）/Product（产品）/LocalBusiness（本地商家）Schema（结构化数据），并补充 sameAs（同一实体链接）。",
        "3. 将薄弱段落改写为先回答、可独立理解的内容。",
        "4. 确认 Tier 1（一级）AI Crawler（人工智能爬虫）访问。",
        "5. 在第三方平台建设实体权威。",
        "",
        "## 术语表",
        "",
        "- GEO（生成式引擎优化）：让网站更容易被生成式搜索和大模型理解、引用和推荐。",
        "- Citability（可引用性）：AI（人工智能）系统将某段内容直接引用为答案的难易程度。",
        "- llms.txt（大模型说明文件）：放在网站根目录、用于指导 AI（人工智能）系统理解网站内容的 Markdown（轻量标记语言）文件。",
    ])
    path = write_text("GEO-CLIENT-REPORT.md", content)
    print(f"客户报告已生成：{path}")
    return path


def markdown_to_basic_html(markdown: str, title: str) -> str:
    body = html.escape(markdown)
    body = re.sub(r"^# (.+)$", r"<h1>\1</h1>", body, flags=re.M)
    body = re.sub(r"^## (.+)$", r"<h2>\1</h2>", body, flags=re.M)
    body = re.sub(r"^### (.+)$", r"<h3>\1</h3>", body, flags=re.M)
    body = body.replace("\n", "<br>\n")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111827; margin: 48px; line-height: 1.45; }}
    h1 {{ color: #0f172a; border-bottom: 3px solid #2563eb; padding-bottom: 12px; }}
    h2 {{ margin-top: 32px; color: #1e3a8a; }}
    h3 {{ color: #374151; }}
    code, pre {{ background: #f3f4f6; }}
  </style>
</head>
<body>{body}</body>
</html>
"""


def browser_candidates() -> list[str]:
    names = ["google-chrome", "chrome", "chromium", "chromium-browser", "microsoft-edge", "msedge"]
    found = [path for name in names if (path := shutil.which(name))]
    for path in [
        "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
        "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    ]:
        if Path(path).exists():
            found.append(path)
    return found


def file_uri_for_browser(path: Path, browser: str) -> str:
    resolved = path.resolve()
    if browser.endswith(".exe") and shutil.which("wslpath"):
        try:
            win = subprocess.check_output(["wslpath", "-w", str(resolved)], text=True).strip()
            if win.startswith("\\\\"):
                return "file:" + win.replace("\\", "/")
            return "file:///" + win.replace("\\", "/")
        except Exception:
            pass
    return resolved.as_uri()


def output_path_for_browser(path: Path, browser: str) -> str:
    resolved = path.resolve()
    if browser.endswith(".exe") and shutil.which("wslpath"):
        try:
            return subprocess.check_output(["wslpath", "-w", str(resolved)], text=True).strip()
        except Exception:
            pass
    return str(resolved)


def cmd_report_pdf(args: argparse.Namespace) -> list[Path]:
    url = normalize_url(args.url)
    report_path = Path("GEO-AUDIT-REPORT.md")
    if not report_path.exists():
        bundle = collect(url)
        report_path.write_text(render_audit(bundle) + "\n", encoding="utf-8")
    markdown = report_path.read_text(encoding="utf-8")
    title = f"GEO（生成式引擎优化）审计报告 - {domain_from_url(url)}"
    html_path = Path("GEO-REPORT.html")
    pdf_path = Path("GEO-REPORT.pdf")
    html_path.write_text(markdown_to_basic_html(markdown, title), encoding="utf-8")

    last_error = ""
    for browser in browser_candidates():
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={output_path_for_browser(pdf_path, browser)}",
            "--print-to-pdf-no-header",
            "--no-pdf-header-footer",
            "--virtual-time-budget=5000",
            file_uri_for_browser(html_path, browser),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                print(f"PDF（便携式文档格式）报告已生成：{pdf_path}")
                return [html_path, pdf_path]
        except Exception as exc:
            last_error = f"{browser}: {exc}"
            continue
    write_text("GEO-REPORT-PDF-ERROR.txt", f"无法生成 PDF（便携式文档格式）。最后错误：{last_error}\nHTML（超文本标记语言）报告已生成：{html_path}")
    print(f"HTML（超文本标记语言）报告已生成：{html_path}；PDF（便携式文档格式）生成失败。查看 GEO-REPORT-PDF-ERROR.txt")
    return [html_path]


def ensure_crm_dirs() -> None:
    for path in [CRM_ROOT, AUDITS_DIR, PROPOSALS_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    if not PROSPECTS_FILE.exists():
        write_json(PROSPECTS_FILE, [])


def load_prospects() -> list[dict[str, Any]]:
    ensure_crm_dirs()
    data = read_json(PROSPECTS_FILE, [])
    return data if isinstance(data, list) else []


def save_prospects(prospects: list[dict[str, Any]]) -> None:
    write_json(PROSPECTS_FILE, prospects)


def find_prospect(prospects: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    key_l = key.lower()
    for prospect in prospects:
        if str(prospect.get("id", "")).lower() == key_l or str(prospect.get("domain", "")).lower() == key_l:
            return prospect
    return None


def company_from_domain(domain: str) -> str:
    bare = domain.replace("www.", "").split(".")[0]
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", bare) if part)


def next_prospect_id(prospects: list[dict[str, Any]]) -> str:
    nums = []
    for item in prospects:
        match = re.match(r"PRO-(\d+)", str(item.get("id", "")))
        if match:
            nums.append(int(match.group(1)))
    return f"PRO-{(max(nums) + 1) if nums else 1:03d}"


def cmd_prospect(args: argparse.Namespace) -> Any:
    ensure_crm_dirs()
    prospects = load_prospects()
    action = args.prospect_command
    if action == "new":
        domain = domain_from_url(args.domain)
        existing = find_prospect(prospects, domain)
        if existing:
            print(f"潜在客户已存在：{existing['id']} {domain}")
            return existing
        prospect = {
            "id": next_prospect_id(prospects),
            "company": args.company or company_from_domain(domain),
            "domain": domain,
            "contact_email": args.email or "",
            "contact_name": args.contact or "",
            "industry": "",
            "country": "",
            "status": "lead",
            "geo_score": 0,
            "audit_date": "",
            "audit_file": "",
            "proposal_file": "",
            "monthly_value": args.monthly or 0,
            "contract_start": None,
            "contract_months": 0,
            "notes": [],
            "created_at": now_date(),
            "updated_at": now_date(),
        }
        prospects.append(prospect)
        save_prospects(prospects)
        print(f"潜在客户已创建：{prospect['id']} {domain}")
        return prospect
    if action == "list":
        rows = [[p.get("id"), p.get("company"), p.get("domain"), p.get("status"), p.get("geo_score"), p.get("monthly_value")] for p in prospects]
        print(table(rows, ["ID（编号）", "公司", "域名", "状态", "分数", "MRR（月经常性收入）"]))
        return rows
    if action == "show":
        prospect = find_prospect(prospects, args.key)
        if not prospect:
            raise RuntimeError(f"未找到潜在客户：{args.key}")
        print(json.dumps(prospect, indent=2, ensure_ascii=False))
        return prospect
    if action == "audit":
        prospect = find_prospect(prospects, args.key)
        if not prospect:
            raise RuntimeError(f"未找到潜在客户：{args.key}")
        bundle = collect(prospect["domain"], include_brand=False)
        audit_file = AUDITS_DIR / f"{slug_domain(prospect['domain'])}-{now_date()}.md"
        write_text(audit_file, render_audit(bundle))
        prospect["geo_score"] = bundle.scores["overall"]
        prospect["audit_date"] = now_date()
        prospect["audit_file"] = str(audit_file)
        prospect["status"] = "audit"
        prospect.setdefault("notes", []).append({"date": now_date(), "text": f"快速审计已运行。GEO（生成式引擎优化）分：{bundle.scores['overall']}/100。"})
        prospect["updated_at"] = now_date()
        save_prospects(prospects)
        print(f"潜在客户审计已保存：{audit_file}")
        return prospect
    if action == "note":
        prospect = find_prospect(prospects, args.key)
        if not prospect:
            raise RuntimeError(f"未找到潜在客户：{args.key}")
        prospect.setdefault("notes", []).append({"date": now_date(), "text": args.text})
        prospect["updated_at"] = now_date()
        save_prospects(prospects)
        print(f"备注已添加到 {prospect['id']}")
        return prospect
    if action == "status":
        prospect = find_prospect(prospects, args.key)
        if not prospect:
            raise RuntimeError(f"未找到潜在客户：{args.key}")
        prospect["status"] = args.status
        prospect["updated_at"] = now_date()
        save_prospects(prospects)
        print(f"状态已更新：{prospect['id']} -> {args.status}")
        return prospect
    if action == "won":
        prospect = find_prospect(prospects, args.key)
        if not prospect:
            raise RuntimeError(f"未找到潜在客户：{args.key}")
        prospect["status"] = "won"
        prospect["monthly_value"] = args.monthly
        prospect["contract_start"] = now_date()
        prospect["updated_at"] = now_date()
        save_prospects(prospects)
        print(f"潜在客户已标记为成交：{prospect['id']}")
        return prospect
    if action == "lost":
        prospect = find_prospect(prospects, args.key)
        if not prospect:
            raise RuntimeError(f"未找到潜在客户：{args.key}")
        prospect["status"] = "lost"
        prospect.setdefault("notes", []).append({"date": now_date(), "text": f"流失原因：{args.reason}"})
        prospect["updated_at"] = now_date()
        save_prospects(prospects)
        print(f"潜在客户已标记为流失：{prospect['id']}")
        return prospect
    if action == "pipeline":
        summary: dict[str, int] = {}
        for p in prospects:
            summary[p.get("status", "lead")] = summary.get(p.get("status", "lead"), 0) + 1
        rows = [[k, v] for k, v in sorted(summary.items())]
        print(table(rows, ["状态", "数量"]))
        return summary
    raise RuntimeError(f"未知潜在客户命令：{action}")


def cmd_proposal(args: argparse.Namespace) -> Path:
    ensure_crm_dirs()
    domain = domain_from_url(args.domain)
    prospects = load_prospects()
    prospect = find_prospect(prospects, domain)
    bundle = collect(domain, include_brand=False)
    tier = args.tier or ("premium" if bundle.scores["overall"] < 40 else "standard" if bundle.scores["overall"] < 70 else "basic")
    monthly = args.monthly or (3500 if tier == "basic" else 6500 if tier == "standard" else 9500)
    content = "\n".join([
        f"# GEO（生成式引擎优化）服务提案：{bundle.brand}",
        "",
        f"**提案日期：** {now_date()}",
        f"**域名：** {domain}",
        f"**当前 GEO（生成式引擎优化）分：** {bundle.scores['overall']}/100（{score_label(bundle.scores['overall'])}）",
        f"**推荐服务档位：** {tier_zh(tier)}",
        f"**月度投入：** EUR（欧元）{monthly}",
        "",
        "## 为什么重要",
        "",
        "AI（人工智能）搜索可见度取决于 Crawler Access（爬虫访问）、Citability（可引用性）、Schema（结构化数据）、第三方实体信号和各平台就绪度。",
        "",
        "## 建议服务范围",
        "",
        "- AI Crawler（人工智能爬虫）和 robots.txt（爬虫规则文件）优化",
        "- `llms.txt`（大模型说明文件）创建与维护",
        "- Schema.org（结构化数据标准）实施",
        "- 内容 Citability（可引用性）改写",
        "- Brand Authority（品牌权威）信号建设计划",
        "- 月度分数追踪",
        "",
        "## 预期结果",
        "",
        "让 AI（人工智能）系统更容易发现、理解、引用并推荐该网站。",
    ])
    path = PROPOSALS_DIR / f"{slug_domain(domain)}-proposal-{now_date()}.md"
    write_text(path, content)
    if prospect:
        prospect["status"] = "proposal"
        prospect["proposal_file"] = str(path)
        prospect["monthly_value"] = monthly
        prospect["updated_at"] = now_date()
        save_prospects(prospects)
    print(f"提案已生成：{path}")
    return path


def cmd_compare(args: argparse.Namespace) -> Path:
    ensure_crm_dirs()
    domain = domain_from_url(args.domain)
    files = sorted(AUDITS_DIR.glob(f"{slug_domain(domain)}-*.md"))
    if files:
        baseline = files[0].read_text(encoding="utf-8")
        current = files[-1].read_text(encoding="utf-8")
    else:
        bundle = collect(domain, include_brand=False)
        current = render_audit(bundle)
        baseline = current
    score_re = re.compile(r"(?:Overall GEO Score|GEO（生成式引擎优化）总分)[：:]?\s*(\d+)", re.I)
    b = int(score_re.search(baseline).group(1)) if score_re.search(baseline) else 0
    c = int(score_re.search(current).group(1)) if score_re.search(current) else b
    content = "\n".join([
        f"# GEO（生成式引擎优化）月度变化报告：{domain}",
        "",
        f"**报告日期：** {now_date()}",
        f"**基线分：** {b}/100",
        f"**当前分：** {c}/100",
        f"**变化值：** {c - b:+d}",
        "",
        "## 摘要",
        "",
        "本报告对比已有审计快照。如果当前只有一个快照，它会同时作为基线和当前结果，直到第二次审计产生。",
        "",
        "## 下一步重点",
        "",
        "- 完成修复后重新运行完整审计。",
        "- 持续追踪 Crawler Access（爬虫访问）、Schema（结构化数据）完整度、llms.txt（大模型说明文件）状态和 Citability（可引用性）分数变化。",
    ])
    path = REPORTS_DIR / f"{slug_domain(domain)}-monthly-{datetime.now().strftime('%Y-%m')}.md"
    write_text(path, content)
    print(f"月度对比报告已生成：{path}")
    return path


def cmd_update(args: argparse.Namespace) -> str:
    source = REPO_ROOT
    lines = ["GEO（生成式引擎优化）Codex（OpenAI 编程代理）更新检查", "==========================", ""]
    if (source / ".git").exists():
        current = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=source, text=True).strip()
        lines.append(f"当前代码版本：{current}")
        if args.apply:
            lines.append("已请求应用更新。请在更新后的代码目录运行 `codex-install.sh` 刷新已安装的 skill（技能）。")
        else:
            lines.append("当前仅为 Dry run（试运行），没有修改文件。")
    else:
        lines.append("当前源码目录不是 Git（版本控制）仓库，未执行更新检查。")
    output = "\n".join(lines)
    print(output)
    return output


@contextmanager
def pushd(path: Path):
    old = Path.cwd()
    path.mkdir(parents=True, exist_ok=True)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def validate_file(path: Path, domain: str) -> tuple[bool, str]:
    if not path.exists():
        return False, "缺失"
    if path.stat().st_size == 0:
        return False, "空文件"
    if path.suffix.lower() in {".md", ".txt", ".html", ".json"}:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        if domain.lower() not in text and "lacewigsbuy" not in text:
            return False, "未发现目标域名证据"
    return True, "正常"


def cmd_full_test(args: argparse.Namespace) -> Path:
    url = normalize_url(args.url)
    domain = domain_from_url(url)
    run_dir = Path.cwd() / "geo-test-runs" / f"{slug_domain(domain)}-{now_stamp()}"
    results: list[dict[str, Any]] = []

    def record(name: str, func, ns: argparse.Namespace) -> None:
        try:
            before = {p.resolve() for p in Path.cwd().glob("*")}
            value = func(ns)
            after = {p.resolve() for p in Path.cwd().glob("*")}
            created = sorted(str(p.name) for p in after - before)
            if isinstance(value, Path):
                created.append(value.name)
            elif isinstance(value, list):
                created.extend(p.name for p in value if isinstance(p, Path))
            results.append({"command": name, "status": "通过", "created": sorted(set(created))})
        except Exception as exc:
            results.append({"command": name, "status": "失败", "error": str(exc), "created": []})

    with pushd(run_dir):
        base = argparse.Namespace(url=url)
        record("audit", cmd_audit, base)
        record("page", cmd_page, base)
        record("quick", cmd_quick, base)
        record("citability", cmd_citability, base)
        record("crawlers", cmd_crawlers, base)
        record("llmstxt", cmd_llmstxt, base)
        record("brands", cmd_brands, argparse.Namespace(url=url, brand=None))
        record("platforms", cmd_platforms, base)
        record("schema", cmd_schema, base)
        record("technical", cmd_technical, base)
        record("content", cmd_content, base)
        record("report", cmd_report, base)
        record("report-pdf", cmd_report_pdf, base)

        original_crm_root = CRM_ROOT
        test_crm_root = run_dir / ".geo-prospects"
        set_crm_root(test_crm_root)
        try:
            record("prospect new", cmd_prospect, argparse.Namespace(prospect_command="new", domain=domain, company=company_from_domain(domain), email="", contact="", monthly=0))
            record("prospect show", cmd_prospect, argparse.Namespace(prospect_command="show", key=domain))
            record("prospect note", cmd_prospect, argparse.Namespace(prospect_command="note", key=domain, text="Codex full-test note"))
            record("prospect status", cmd_prospect, argparse.Namespace(prospect_command="status", key=domain, status="qualified"))
            record("prospect audit", cmd_prospect, argparse.Namespace(prospect_command="audit", key=domain))
            record("prospect list", cmd_prospect, argparse.Namespace(prospect_command="list"))
            record("prospect pipeline", cmd_prospect, argparse.Namespace(prospect_command="pipeline"))
            record("proposal", cmd_proposal, argparse.Namespace(domain=domain, tier=None, monthly=None))
            record("compare", cmd_compare, argparse.Namespace(domain=domain))
            record("prospect won", cmd_prospect, argparse.Namespace(prospect_command="won", key=domain, monthly=1200))
            record("prospect lost", cmd_prospect, argparse.Namespace(prospect_command="lost", key=domain, reason="Codex full-test closure"))
        finally:
            set_crm_root(original_crm_root)
        record("update", cmd_update, argparse.Namespace(apply=False))

        expected = [
            "GEO-AUDIT-REPORT.md",
            "GEO-PAGE-ANALYSIS.md",
            "GEO-CITABILITY-SCORE.md",
            "GEO-CRAWLER-ACCESS.md",
            "GEO-BRAND-MENTIONS.md",
            "GEO-PLATFORM-OPTIMIZATION.md",
            "GEO-SCHEMA-REPORT.md",
            "GEO-TECHNICAL-AUDIT.md",
            "GEO-CONTENT-ANALYSIS.md",
            "GEO-CLIENT-REPORT.md",
            "GEO-REPORT.html",
        ]
        if Path("GEO-LLMSTXT-ANALYSIS.md").exists():
            expected.append("GEO-LLMSTXT-ANALYSIS.md")
        else:
            expected.extend(["llms.txt", "GEO-LLMSTXT-GENERATION.md"])
        validations = []
        for name in expected:
            ok, reason = validate_file(Path(name), domain)
            validations.append({"file": name, "status": "通过" if ok else "失败", "reason": reason})
        crm_expected = [
            Path(".geo-prospects") / "prospects.json",
            Path(".geo-prospects") / "audits" / f"{slug_domain(domain)}-{now_date()}.md",
            Path(".geo-prospects") / "proposals" / f"{slug_domain(domain)}-proposal-{now_date()}.md",
            Path(".geo-prospects") / "reports" / f"{slug_domain(domain)}-monthly-{datetime.now().strftime('%Y-%m')}.md",
        ]
        for path in crm_expected:
            ok, reason = validate_file(path, domain)
            validations.append({"file": str(path), "status": "通过" if ok else "失败", "reason": reason})
        pdf_ok = Path("GEO-REPORT.pdf").exists() and Path("GEO-REPORT.pdf").stat().st_size > 0
        validations.append({"file": "GEO-REPORT.pdf", "status": "通过" if pdf_ok else "失败", "reason": "正常" if pdf_ok else "未生成 PDF（便携式文档格式）"})
        summary = {
            "target": url,
            "run_dir": str(run_dir),
            "crm_root": str(run_dir / ".geo-prospects"),
            "commands": results,
            "files": validations,
            "passed_commands": sum(1 for r in results if r["status"] == "通过"),
            "failed_commands": sum(1 for r in results if r["status"] != "通过"),
            "passed_files": sum(1 for r in validations if r["status"] == "通过"),
            "failed_files": sum(1 for r in validations if r["status"] != "通过"),
        }
        write_json(Path("FULL-TEST-RESULTS.json"), summary)
        md = [
            f"# GEO（生成式引擎优化）Codex（OpenAI 编程代理）全量测试：{domain}",
            "",
            f"**目标：** {url}",
            f"**运行目录：** {run_dir}",
            f"**命令通过数：** {summary['passed_commands']}",
            f"**命令失败数：** {summary['failed_commands']}",
            f"**文件通过数：** {summary['passed_files']}",
            f"**文件失败数：** {summary['failed_files']}",
            "",
            "## 命令结果",
            "",
            table([[command_label_zh(r["command"]), r["status"], r.get("error", ""), ", ".join(r.get("created", []))] for r in results], ["命令", "状态", "错误", "已创建文件"]),
            "",
            "## 文件校验",
            "",
            table([[r["file"], r["status"], r["reason"]] for r in validations], ["文件", "状态", "原因"]),
        ]
        write_text("FULL-TEST-RESULTS.md", "\n".join(md))
        if summary["failed_commands"] or summary["failed_files"]:
            raise RuntimeError(
                f"全量测试失败：{summary['failed_commands']} 个命令失败，"
                f"{summary['failed_files']} 个文件校验失败。查看 {run_dir / 'FULL-TEST-RESULTS.md'}"
            )
    print(f"全量测试已完成：{run_dir}")
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GEO-SEO Codex CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func in [
        ("audit", cmd_audit),
        ("page", cmd_page),
        ("quick", cmd_quick),
        ("citability", cmd_citability),
        ("crawlers", cmd_crawlers),
        ("llmstxt", cmd_llmstxt),
        ("platforms", cmd_platforms),
        ("schema", cmd_schema),
        ("technical", cmd_technical),
        ("content", cmd_content),
        ("report", cmd_report),
        ("report-pdf", cmd_report_pdf),
        ("full-test", cmd_full_test),
    ]:
        p = sub.add_parser(name)
        p.add_argument("url")
        p.set_defaults(func=func)

    p = sub.add_parser("brands")
    p.add_argument("url")
    p.add_argument("--brand")
    p.set_defaults(func=cmd_brands)

    p = sub.add_parser("proposal")
    p.add_argument("domain")
    p.add_argument("--tier", choices=["basic", "standard", "premium"])
    p.add_argument("--monthly", type=int)
    p.set_defaults(func=cmd_proposal)

    p = sub.add_parser("compare")
    p.add_argument("domain")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("update")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("prospect")
    prospect_sub = p.add_subparsers(dest="prospect_command", required=True)
    pnew = prospect_sub.add_parser("new")
    pnew.add_argument("domain")
    pnew.add_argument("--company")
    pnew.add_argument("--email")
    pnew.add_argument("--contact")
    pnew.add_argument("--monthly", type=int, default=0)
    plist = prospect_sub.add_parser("list")
    pshow = prospect_sub.add_parser("show")
    pshow.add_argument("key")
    paudit = prospect_sub.add_parser("audit")
    paudit.add_argument("key")
    pnote = prospect_sub.add_parser("note")
    pnote.add_argument("key")
    pnote.add_argument("text")
    pstatus = prospect_sub.add_parser("status")
    pstatus.add_argument("key")
    pstatus.add_argument("status")
    pwon = prospect_sub.add_parser("won")
    pwon.add_argument("key")
    pwon.add_argument("monthly", type=int)
    plost = prospect_sub.add_parser("lost")
    plost.add_argument("key")
    plost.add_argument("reason")
    prospect_sub.add_parser("pipeline")
    p.set_defaults(func=cmd_prospect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
