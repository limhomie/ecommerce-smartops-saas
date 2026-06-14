"""Web crawler tool — extracts clean content from web pages for RAG ingestion."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class CrawledPage:
    url: str
    title: str
    text: str
    links: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class WebCrawler:
    """Simple web crawler that extracts clean text content from pages."""

    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.domain = urlparse(base_url).netloc

    def fetch(self, path: str = "/") -> CrawledPage | None:
        """Fetch and parse a single page."""
        url = urljoin(self.base_url, path)
        try:
            resp = httpx.get(url, timeout=self.timeout, follow_redirects=True,
                           headers={"User-Agent": "Mozilla/5.0 EcomAgent/1.0"})
            if resp.status_code != 200:
                return None
            return self._parse(url, resp.text)
        except Exception:
            return None

    def fetch_all(self, paths: list[str], delay: float = 0.5) -> list[CrawledPage]:
        """Fetch multiple pages with polite delay."""
        results = []
        for path in paths:
            page = self.fetch(path)
            if page:
                results.append(page)
            time.sleep(delay)
        return results

    def discover_links(self, html: str, same_domain: bool = True) -> list[str]:
        """Extract all links from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.startswith("javascript"):
                continue
            full = urljoin(self.base_url, href)
            if same_domain and self.domain not in full:
                continue
            links.append(full)
        return list(set(links))

    def _parse(self, url: str, html: str) -> CrawledPage:
        soup = BeautifulSoup(html, "html.parser")

        # Remove noise elements
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "iframe"]):
            tag.decompose()
        # Remove common navigation/sidebar containers
        for cls in ["nav", "menu", "sidebar", "footer", "header", "breadcrumb", "pagination"]:
            for tag in soup.find_all(class_=re.compile(cls, re.I)):
                tag.decompose()
            for tag in soup.find_all(id=re.compile(cls, re.I)):
                tag.decompose()

        title = soup.title.string.strip() if soup.title else url

        # Extract main content — prefer article/main tags, fallback to body
        main = soup.find("article") or soup.find("main") or soup.find("body")
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # SPA fallback: also extract meta descriptions, JSON-LD, and noscript content
        extra_text = []
        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            extra_text.append(meta_desc["content"])
        # JSON-LD structured data
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    desc = data.get("description", "")
                    if desc:
                        extra_text.append(str(desc))
            except Exception:
                pass
        # Noscript fallback
        noscript = soup.find("noscript")
        if noscript:
            ns_text = noscript.get_text(separator="\n", strip=True)
            if len(ns_text) > 50:
                extra_text.append(ns_text)
        # Alt text from images
        for img in soup.find_all("img", alt=True):
            alt = img["alt"].strip()
            if len(alt) > 2 and alt not in ("Logo", "logo", "icon"):
                extra_text.append(alt)

        if extra_text:
            text = text + "\n\n" + "\n".join(extra_text)

        # Clean up: collapse whitespace, remove junk lines
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if not line or len(line) <= 2:
                continue
            # Skip common nav/UI junk
            if line in ("Chinese", "English", "首页", "返回", "TOP", "↑",
                        "品牌理念", "新品推荐", "实体店铺", "新闻资讯",
                        "百度百科", "关于公司", "会员专享", "加入我们",
                        "联系方式", "天猫商城", "招商加盟", "关注平台",
                        "网站地图", "中文", "English"):
                continue
            lines.append(line)
        text = "\n".join(lines)

        # Remove repeated navigation patterns (same text block appearing on every page)
        # Common HSIA nav footer
        for pattern in [
            r"粤ICP备\d+号\s*©\s*\d{4}\s*HSIA\s*All rights reserved\s*\|?\s*技术支持：\S+",
            r"实体店铺\s*\|\s*网站地图\s*\|\s*粤ICP备\d+号",
        ]:
            text = re.sub(pattern, "", text)

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()

        # Extract links
        links = self.discover_links(html)

        return CrawledPage(url=url, title=title, text=text, links=links)
