#!/usr/bin/env python3
"""Phase 1: Crawl competing lingerie brands → classify → RAG ingest.

Sources: HSIA官网, 蕉内官网, 百度百科

Run: D:/anaconda/python.exe scripts/crawl_competitors.py
"""

from __future__ import annotations

import sys, os, time, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Settings, ROOT_DIR
from src.tools.web_crawler import WebCrawler
from src.memory.vector_store import VectorStore
from src.memory.long_term import LongTermMemory
from src.observability.logger import get_logger, configure_logging

logger = get_logger(__name__)

# ═══════════════════════════════════════════════
# Brand data sources
# ═══════════════════════════════════════════════

HSIA_PAGES = [
    ("/", "首页/品牌文化"),
    ("/Brand/Brand.html", "品牌理念"),
    ("/news/news.html", "新闻资讯"),
    ("/Shop/Shop.html", "实体店铺"),
    ("/About/About.html", "公司简介"),
    ("/Join.html", "招商加盟"),
]

BANANAIN_HOMEPAGE = {
    "url": "https://www.bananain.com",
    "label": "蕉内品牌首页",
}

# Baidu Baike pages for brands we can't reach directly
BAIDU_BAIKE = [
    ("https://baike.baidu.com", "/item/%E8%95%89%E5%86%85", "蕉内"),
    ("https://baike.baidu.com", "/item/UBRAS", "Ubras"),
    ("https://baike.baidu.com", "/item/%E5%86%85%E5%A4%96/22727282", "NEIWAI内外"),
]


def crawl_and_ingest():
    settings = Settings()
    configure_logging(settings)

    logger.info("phase1_crawl_start")

    store = VectorStore(settings)
    ltm = LongTermMemory(store)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    results = {"pages": 0, "chunks": 0}

    # ── 1. HSIA (multi-page) ──
    logger.info("crawling_hsia")
    hsia = WebCrawler("https://www.chinahsia.com")
    for path, label in HSIA_PAGES:
        try:
            page = hsia.fetch(path)
            if not page or len(page.text) < 30:
                continue
            text = f"""# [HSIA遐] {label}
来源: {page.url} | 抓取时间: {now}

{page.text}
"""
            chunks = ltm.ingest_document("competitors", text, {
                "brand": "HSIA", "category": label, "url": page.url,
                "crawled_at": now, "source": "phase1_crawler",
            })
            results["pages"] += 1
            results["chunks"] += chunks
            logger.info("hsia_page", path=path, label=label, chunks=chunks)
            time.sleep(0.8)
        except Exception as e:
            logger.warning("hsia_error", path=path, error=str(e))

    # ── 2. Bananain (single-page) ──
    logger.info("crawling_bananain")
    try:
        bn = WebCrawler("https://www.bananain.com")
        page = bn.fetch("/")
        if page and len(page.text) > 80:
            text = f"""# [蕉内Bananain] 品牌首页
来源: {page.url} | 抓取时间: {now}
品牌定位: 体感科学公司

{page.text}
"""
            chunks = ltm.ingest_document("competitors", text, {
                "brand": "蕉内", "category": "品牌首页", "url": page.url,
                "crawled_at": now, "source": "phase1_crawler",
            })
            results["pages"] += 1
            results["chunks"] += chunks
            logger.info("bananain_page", chunks=chunks)
    except Exception as e:
        logger.warning("bananain_error", error=str(e))

    # ── 3. Baidu Baike ──
    logger.info("crawling_baike")
    for base_url, path, brand in BAIDU_BAIKE:
        try:
            crawler = WebCrawler(base_url)
            page = crawler.fetch(path)
            if not page or len(page.text) < 100:
                logger.warning("baike_empty", brand=brand)
                continue

            text = f"""# [{brand}] 百度百科
来源: {page.url} | 抓取时间: {now}

{page.text[:8000]}
"""
            chunks = ltm.ingest_document("competitors", text, {
                "brand": brand, "category": "百度百科", "url": page.url,
                "crawled_at": now, "source": "phase1_crawler_baike",
            })
            results["pages"] += 1
            results["chunks"] += chunks
            logger.info("baike_page", brand=brand, chunks=chunks)
            time.sleep(1.5)  # Slower for Baidu
        except Exception as e:
            logger.warning("baike_error", brand=brand, error=str(e))

    # ── Summary ──
    logger.info("phase1_crawl_done", **results)
    print(f"\n{'='*60}")
    print(f"Phase 1 竞品爬取完成 — {now}")
    print(f"  页面: {results['pages']} 个")
    print(f"  向量块: {results['chunks']} 个")
    print(f"{'='*60}")

    stats = ltm.get_stats()
    print("\n知识库全览:")
    for coll, count in sorted(stats.items()):
        print(f"  {coll}: {count} 块")

    return results


def _extract_sections(text: str, keywords: list[str]) -> list[str]:
    """Try to split text into sections around keywords."""
    # Simple approach: find keyword positions and split
    sections = []
    for kw in keywords:
        idx = text.find(kw)
        if idx >= 0:
            start = max(0, idx - 50)
            end = min(len(text), idx + 300)
            sections.append(text[start:end].strip())
    return sections


if __name__ == "__main__":
    crawl_and_ingest()
