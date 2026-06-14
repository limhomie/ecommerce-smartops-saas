#!/usr/bin/env python3
"""Daily crawler: fetch HSIA (遐) brand content → classify → RAG ingest.

Run: D:/anaconda/python.exe scripts/crawl_hsia.py
"""

from __future__ import annotations

import sys, os, time, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Settings, ROOT_DIR
from src.tools.web_crawler import WebCrawler
from src.memory.vector_store import VectorStore
from src.memory.long_term import LongTermMemory, COLLECTION_COMPETITORS, COLLECTION_WIKI
from src.observability.logger import get_logger, configure_logging

logger = get_logger(__name__)

BASE_URL = "https://www.chinahsia.com"

# Pages to crawl: (path, classification, label)
PAGES = [
    ("/Brand/Brand.html", "competitors", "品牌理念"),
    ("/news/news.html", "competitors", "新闻资讯"),
    ("/Shop/Shop.html", "competitors", "实体店铺"),
    ("/About/About.html", "competitors", "公司简介"),
    ("/Join.html", "competitors", "招商加盟"),
    ("/Recruitment.html", "wiki", "人才招聘"),
    ("/Contact.html", "wiki", "联系方式"),
]


def crawl_and_ingest():
    settings = Settings()
    configure_logging(settings)

    logger.info("hsia_crawl_start", base_url=BASE_URL)

    crawler = WebCrawler(BASE_URL)
    store = VectorStore(settings)
    ltm = LongTermMemory(store)

    results = {"new_chunks": 0, "pages": 0, "collections": {}}

    for path, collection, label in PAGES:
        try:
            page = crawler.fetch(path)
            if not page:
                logger.warning("fetch_failed", path=path)
                continue

            # Build structured content with metadata header
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            structured = f"""# {page.title}
来源: {page.url}
抓取时间: {now}
分类: {label}

{page.text}
"""
            # Ingest into ChromaDB
            chunks = ltm.ingest_document(
                collection,
                structured,
                {
                    "url": page.url,
                    "title": page.title,
                    "category": label,
                    "crawled_at": now,
                    "source": "hsia_crawler",
                },
            )

            results["pages"] += 1
            results["new_chunks"] += chunks
            results["collections"][collection] = results["collections"].get(collection, 0) + chunks

            logger.info("page_ingested", path=path, collection=collection, chunks=chunks)
            time.sleep(0.5)  # Polite delay

        except Exception as e:
            logger.error("crawl_error", path=path, error=str(e))

    # Also crawl the homepage for brand story / culture
    try:
        homepage = crawler.fetch("/")
        if homepage:
            # Extract brand info section from homepage
            brand_text = homepage.text
            # Focus on meaningful content between "品牌文化" and "关于公司"
            culture_match = re.search(r"品牌文化(.*?)关于公司", brand_text, re.S)
            if culture_match:
                brand_content = f"# HSIA 品牌文化\n来源: {BASE_URL}/\n\n{culture_match.group(1).strip()}"
                chunks = ltm.ingest_document(
                    "competitors",
                    brand_content,
                    {"url": BASE_URL, "title": "HSIA 品牌文化", "category": "品牌文化",
                     "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "source": "hsia_crawler"},
                )
                results["pages"] += 1
                results["new_chunks"] += chunks
                results["collections"]["competitors"] = results["collections"].get("competitors", 0) + chunks
    except Exception as e:
        logger.error("homepage_error", error=str(e))

    # Summary
    logger.info("hsia_crawl_done", **results)
    print(f"\n{'='*50}")
    print(f"HSIA 爬取完成 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  抓取页面: {results['pages']} 个")
    print(f"  新增向量块: {results['new_chunks']} 个")
    for coll, count in results["collections"].items():
        print(f"    → {coll}: +{count} 块")
    print(f"{'='*50}")

    # Print current stats
    stats = ltm.get_stats()
    print("\n知识库总览:")
    for coll, count in sorted(stats.items()):
        print(f"  {coll}: {count} 块")

    return results


if __name__ == "__main__":
    crawl_and_ingest()
