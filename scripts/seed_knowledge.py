#!/usr/bin/env python3
"""Seed knowledge base with sample product data and enterprise wiki content.

Run: D:/anaconda/python.exe scripts/seed_knowledge.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import Settings, ROOT_DIR
from src.llm import set_llm
from src.llm.factory import create_llm_from_settings
from src.memory.vector_store import VectorStore
from src.memory.long_term import LongTermMemory
from src.observability.logger import get_logger, configure_logging

logger = get_logger(__name__)


def main():
    settings = Settings()
    configure_logging(settings)

    # Initialize LLM (respects LLM_PROVIDER from .env)
    try:
        llm = create_llm_from_settings(settings)
        set_llm(llm)
        logger.info("llm_initialized", provider=settings.llm_provider)
    except Exception as e:
        logger.warning("llm_init_failed", error=str(e))

    logger.info("seeding_knowledge_base")

    store = VectorStore(settings)
    lt = LongTermMemory(store)

    # ── Ingest product documents ──
    product_dir = ROOT_DIR / "data" / "documents" / "products"
    if product_dir.exists():
        count = lt.ingest_directory("products", product_dir)
        logger.info("products_ingested", chunks=count)

    # ── Ingest seed competitor data ──
    competitor_data = """
竞品A — 基础款有机棉T恤
- 价格: $19.99
- 材质: 普通有机棉，非GOTS认证
- 评分: 4.0 (1200条评论)
- 核心卖点: 极致性价比
- 广告策略: Facebook轮播广告 + 5% Newsletter折扣
- 最近动态: 6月降价15%，从$23.50降至$19.99

竞品B — 高端有机棉T恤
- 价格: $34.99
- 材质: Supima棉+有机棉混纺
- 评分: 4.5 (890条评论)
- 核心卖点: 高端面料+精致工艺
- 广告策略: Instagram KOL种草 + 小红书素人测评
- 最近动态: 推出「买二送一」限时活动

竞品C — 环保概念T恤
- 价格: $29.99
- 材质: 回收聚酯+有机棉混纺
- 评分: 4.3 (1500条评论)
- 核心卖点: 海洋塑料回收计划
- 广告策略: 公益营销 + YouTube开箱视频
- 最近动态: 与环保NGO联名推出限定款
"""
    lt.ingest_document("competitors", competitor_data, {"type": "competitor_analysis"})

    # ── Ingest ad history ──
    ad_data = """
爆款广告案例1 — 夏季新品上市
- 平台: Facebook + Instagram
- 广告格式: 视频广告 (15s)
- 标题: "夏天不闷汗的秘密，藏在面料里"
- CTR: 3.8%
- ROAS: 4.2x
- 转化率: 2.9%
- 投放时长: 7天
- 花费: $2,500
- 关键学习: 视频前3秒展示面料透气测试效果最佳

爆款广告案例2 — 限时特惠
- 平台: Facebook
- 广告格式: 轮播广告
- 标题: "48小时闪购 | 有机棉T恤低至8折"
- CTR: 4.1%
- ROAS: 5.1x
- 转化率: 3.5%
- 投放时长: 2天
- 花费: $1,200
- 关键学习: 紧迫感+明确折扣信息驱动冲动消费
"""
    lt.ingest_document("ads_history", ad_data, {"type": "ad_case_study"})

    # ── Ingest enterprise wiki ──
    wiki_data = """
公司运营知识库

## 运营SOP
1. 每日运营检查清单
   - 查看前日销售数据和异常指标
   - 检查库存预警和采购建议
   - 回复客户评价和问题
   - 监控竞品价格和促销动态

2. 周度运营流程
   - 每周一: 生成上周运营周报
   - 每周三: 竞品分析和市场调研
   - 每周五: 下周营销计划制定

## 常用工具和账号
- 店铺后台: admin.xxx.com
- ERP系统: erp.xxx.com
- 数据看板: analytics.xxx.com
- 客服系统: service.xxx.com

## 品牌定位
- 核心价值: 环保、品质、透明
- 目标客群: 25-40岁注重健康和环保的都市中产
- 品牌调性: 自然、简约、温暖
- 差异化: GOTS认证 + 全产业链透明可追溯
"""
    lt.ingest_document("enterprise_wiki", wiki_data, {"type": "internal_wiki"})

    # ── Print summary ──
    stats = lt.get_stats()
    logger.info("seed_complete", stats=stats)
    print("\n知识库种子数据已就绪：")
    for coll, count in stats.items():
        print(f"  {coll}: {count} 条记录")


if __name__ == "__main__":
    main()
