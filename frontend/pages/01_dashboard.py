"""Operations Dashboard — interactive date filter with fully dynamic data."""

from __future__ import annotations

import datetime as dt
import random
import hashlib

import streamlit as st

st.set_page_config(page_title="运营仪表盘", page_icon="📊", layout="wide")

st.title("运营仪表盘")

# ── Date range selector ──
col_d1, col_d2, col_d3 = st.columns([1, 1, 2])
with col_d1:
    range_preset = st.selectbox(
        "时间范围",
        ["本周", "上周", "本月", "上月", "自定义"],
        key="range_preset",
    )
with col_d2:
    if range_preset == "自定义":
        start_date = st.date_input("开始", value=dt.date.today() - dt.timedelta(days=7))
        end_date = st.date_input("结束", value=dt.date.today())
    else:
        today = dt.date.today()
        if range_preset == "本周":
            start_date = today - dt.timedelta(days=today.weekday())
            end_date = today
        elif range_preset == "上周":
            last_monday = today - dt.timedelta(days=today.weekday() + 7)
            start_date = last_monday
            end_date = last_monday + dt.timedelta(days=6)
        elif range_preset == "本月":
            start_date = today.replace(day=1)
            end_date = today
        else:
            first = today.replace(day=1)
            end_date = first - dt.timedelta(days=1)
            start_date = end_date.replace(day=1)
        st.caption(f"{start_date.strftime('%m/%d')} — {end_date.strftime('%m/%d')}")

with col_d3:
    if st.button("刷新数据", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Data: preset periods ──
PERIOD_DATA = {
    "本周": {
        "conversion": 2.1, "prev_conversion": 3.4, "aov": 45.60, "prev_aov": 43.30,
        "orders": 534, "prev_orders": 623, "visitors": 25430, "prev_visitors": 24200,
        "bounce": 61, "prev_bounce": 42, "return_rate": 5.2, "prev_return": 4.1,
        "trend_labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        "trend_current": [3.4,3.2,3.0,2.5,2.1,2.3,2.1],
        "trend_prev":    [3.6,3.5,3.6,3.4,3.5,3.3,3.4],
        "orders_daily":  [89,82,78,71,65,72,77],
        "funnel_visitors": 25430, "funnel_product": 15200, "funnel_cart": 3200,
        "funnel_checkout": 1200, "funnel_orders": 534,
        "traffic": ["自然搜索","付费广告","社交媒体","直接访问","邮件营销"],
        "traffic_v": [30, 35, 18, 10, 7],
        "sent_pos": 65, "sent_neu": 25, "sent_neg": 10,
        "rating": [42, 30, 16, 8, 4],
    },
    "上周": {
        "conversion": 3.4, "prev_conversion": 3.1, "aov": 43.30, "prev_aov": 44.10,
        "orders": 623, "prev_orders": 580, "visitors": 18320, "prev_visitors": 18700,
        "bounce": 42, "prev_bounce": 45, "return_rate": 4.1, "prev_return": 3.8,
        "trend_labels": ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
        "trend_current": [3.6,3.5,3.6,3.4,3.5,3.3,3.4],
        "trend_prev":    [3.3,3.2,3.1,3.0,3.1,3.2,3.1],
        "orders_daily":  [95,90,92,88,85,86,87],
        "funnel_visitors": 18320, "funnel_product": 11800, "funnel_cart": 2800,
        "funnel_checkout": 1100, "funnel_orders": 623,
        "traffic": ["自然搜索","付费广告","社交媒体","直接访问","邮件营销"],
        "traffic_v": [38, 25, 15, 14, 8],
        "sent_pos": 72, "sent_neu": 20, "sent_neg": 8,
        "rating": [50, 25, 15, 6, 4],
    },
    "本月": {
        "conversion": 2.7, "prev_conversion": 2.9, "aov": 44.80, "prev_aov": 43.90,
        "orders": 2150, "prev_orders": 2300, "visitors": 79600, "prev_visitors": 79300,
        "bounce": 52, "prev_bounce": 49, "return_rate": 4.7, "prev_return": 4.3,
        "trend_labels": ["W1","W2","W3","W4"],
        "trend_current": [3.1,2.8,2.9,2.1],
        "trend_prev":    [3.2,3.0,2.8,2.9],
        "orders_daily":  [580,560,540,470],
        "funnel_visitors": 79600, "funnel_product": 51000, "funnel_cart": 12000,
        "funnel_checkout": 4500, "funnel_orders": 2150,
        "traffic": ["自然搜索","付费广告","社交媒体","直接访问","邮件营销"],
        "traffic_v": [33, 28, 16, 15, 8],
        "sent_pos": 68, "sent_neu": 22, "sent_neg": 10,
        "rating": [45, 28, 15, 7, 5],
    },
    "上月": {
        "conversion": 2.9, "prev_conversion": 3.0, "aov": 43.90, "prev_aov": 45.00,
        "orders": 2300, "prev_orders": 2100, "visitors": 79300, "prev_visitors": 70000,
        "bounce": 49, "prev_bounce": 51, "return_rate": 4.3, "prev_return": 4.5,
        "trend_labels": ["W1","W2","W3","W4"],
        "trend_current": [3.2,3.0,2.8,2.9],
        "trend_prev":    [3.0,3.1,3.1,3.0],
        "orders_daily":  [600,580,570,550],
        "funnel_visitors": 79300, "funnel_product": 52000, "funnel_cart": 11000,
        "funnel_checkout": 4200, "funnel_orders": 2300,
        "traffic": ["自然搜索","付费广告","社交媒体","直接访问","邮件营销"],
        "traffic_v": [35, 27, 18, 13, 7],
        "sent_pos": 70, "sent_neu": 22, "sent_neg": 8,
        "rating": [48, 27, 14, 7, 4],
    },
}

# ── Custom date range: generate dynamic data ──
def _make_custom(start: dt.date, end: dt.date) -> dict:
    days = (end - start).days + 1
    seed = int(hashlib.md5(f"{start}{end}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    base_conv = round(rng.uniform(2.0, 3.5), 1)
    base_aov = round(rng.uniform(40, 50), 2)
    base_ord = int(rng.uniform(50, 120)) * days
    base_vis = int(rng.uniform(2000, 5000)) * days

    if days <= 14:
        labels = [(start + dt.timedelta(days=i)).strftime("%m/%d") for i in range(days)]
    else:
        labels = [f"W{i+1}" for i in range(min(days // 7 + 1, 6))]

    n = len(labels)
    c_cur = [round(base_conv + rng.uniform(-0.8, 0.5), 1) for _ in range(n)]
    c_prv = [round(c + rng.uniform(-0.3, 0.8), 1) for c in c_cur]
    o_dly = [int(base_ord / max(n, 1) * rng.uniform(0.7, 1.3)) for _ in range(n)]

    t_src = rng.sample([15, 20, 25, 30, 35, 38, 40], 5)
    t_src = [int(s * rng.uniform(0.8, 1.2)) for s in t_src]
    total_t = sum(t_src)
    t_src = [int(s / total_t * 100) for s in t_src]
    t_src[-1] = 100 - sum(t_src[:-1])

    s_pos = int(rng.uniform(55, 78))
    s_neu = int(rng.uniform(15, 28))
    s_neg = 100 - s_pos - s_neu

    r5 = int(rng.uniform(35, 52))
    r4 = int(rng.uniform(22, 32))
    r3 = int(rng.uniform(10, 20))
    r2 = int(rng.uniform(4, 10))
    r1 = 100 - r5 - r4 - r3 - r2

    return {
        "conversion": round(sum(c_cur) / n, 1),
        "prev_conversion": round(sum(c_prv) / n, 1),
        "aov": base_aov, "prev_aov": round(base_aov + rng.uniform(-3, 3), 2),
        "orders": sum(o_dly), "prev_orders": int(sum(o_dly) * rng.uniform(0.85, 1.2)),
        "visitors": base_vis, "prev_visitors": int(base_vis * rng.uniform(0.8, 1.1)),
        "bounce": int(rng.uniform(38, 65)), "prev_bounce": int(rng.uniform(38, 60)),
        "return_rate": round(rng.uniform(3.5, 6.5), 1), "prev_return": round(rng.uniform(3.5, 6.0), 1),
        "trend_labels": labels, "trend_current": c_cur, "trend_prev": c_prv,
        "orders_daily": o_dly,
        "funnel_visitors": base_vis,
        "funnel_product": int(base_vis * rng.uniform(0.5, 0.7)),
        "funnel_cart": int(base_vis * rng.uniform(0.1, 0.2)),
        "funnel_checkout": int(base_vis * rng.uniform(0.04, 0.08)),
        "funnel_orders": sum(o_dly),
        "traffic": ["自然搜索","付费广告","社交媒体","直接访问","邮件营销"],
        "traffic_v": t_src,
        "sent_pos": s_pos, "sent_neu": s_neu, "sent_neg": s_neg,
        "rating": [r5, r4, r3, r2, r1],
    }


if range_preset == "自定义":
    d = _make_custom(start_date, end_date)
    period = f"{start_date.strftime('%m/%d')}-{end_date.strftime('%m/%d')}"
else:
    d = PERIOD_DATA.get(range_preset, PERIOD_DATA["本周"])
    period = range_preset

# ── Helpers ──
def _delta(cur, prev):
    pct = round((cur - prev) / prev * 100, 1) if prev else 0
    return f"{'↑' if pct>0 else '↓' if pct<0 else ''} {abs(pct)}%"

# ── Key metrics ──
st.subheader("核心指标")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("转化率", f"{d['conversion']}%", _delta(d["conversion"], d["prev_conversion"]),
          delta_color="normal" if d["conversion"]>=d["prev_conversion"] else "inverse")
m2.metric("客单价", f"${d['aov']:.2f}", _delta(d["aov"], d["prev_aov"]),
          delta_color="normal" if d["aov"]>=d["prev_aov"] else "inverse")
m3.metric("订单数", f"{d['orders']:,}", f"{d['orders']-d['prev_orders']:+}",
          delta_color="normal" if d["orders"]>=d["prev_orders"] else "inverse")
m4.metric("访客数", f"{d['visitors']:,}", f"{d['visitors']-d['prev_visitors']:+,}", delta_color="normal")
m5.metric("跳出率", f"{d['bounce']}%", f"{d['bounce']-d['prev_bounce']:+}%", delta_color="inverse")
m6.metric("退货率", f"{d['return_rate']}%", f"{d['return_rate']-d['prev_return']:+.1f}%", delta_color="inverse")
st.divider()

# ── Charts ──
from src.utils.chart_utils import (
    conversion_trend_chart, traffic_source_pie, conversion_funnel,
    competitor_price_chart, order_trend_bar, sentiment_gauge, rating_distribution,
)

trend_d = {"labels": d["trend_labels"], "current": d["trend_current"], "previous": d["trend_prev"]}
funnel_d = {
    "stages": ["访客","商品页浏览","加购","发起结账","下单"],
    "values": [d["funnel_visitors"], d["funnel_product"], d["funnel_cart"],
               d["funnel_checkout"], d["funnel_orders"]],
    "rates": ["100%", f"{d['funnel_product']/d['funnel_visitors']*100:.1f}%",
              f"{d['funnel_cart']/d['funnel_visitors']*100:.1f}%",
              f"{d['funnel_checkout']/d['funnel_visitors']*100:.1f}%", f"{d['conversion']}%"],
}
order_d = {"labels": d["trend_labels"], "values": d["orders_daily"]}
traffic_d = {"labels": d["traffic"], "values": d["traffic_v"]}
sent_d = {"labels": d["traffic"], "values": d["traffic_v"]}  # (unused, kept for compat)
rating_d = {"ratings": ["5星","4星","3星","2星","1星"], "percentages": d["rating"]}

st.subheader("转化分析")
col1, col2, col3 = st.columns(3)
with col1:
    st.plotly_chart(conversion_trend_chart(trend_d), use_container_width=True)
with col2:
    st.plotly_chart(conversion_funnel(funnel_d), use_container_width=True)
with col3:
    st.plotly_chart(traffic_source_pie(traffic_d), use_container_width=True)

st.divider()

st.subheader("竞品 & 订单")
col4, col5 = st.columns(2)
with col4:
    st.plotly_chart(competitor_price_chart(), use_container_width=True)
with col5:
    st.plotly_chart(order_trend_bar(order_d), use_container_width=True)

st.divider()

st.subheader("舆情分析")
col6, col7 = st.columns(2)
with col6:
    st.plotly_chart(sentiment_gauge(d["sent_pos"], d["sent_neu"], d["sent_neg"]), use_container_width=True)
with col7:
    st.plotly_chart(rating_distribution(rating_d), use_container_width=True)

st.divider()

# ── Alerts ──
st.subheader("系统告警")
if d["conversion"] < d["prev_conversion"]:
    st.warning(f"转化率同比下降 {_delta(d['conversion'], d['prev_conversion'])}，建议关注竞品动态和流量质量")
if d["bounce"] > 55:
    st.warning(f"跳出率 {d['bounce']}%，偏高，检查页面加载速度和 A+ 内容质量")
if d["return_rate"] > d["prev_return"]:
    st.warning(f"退货率上升至 {d['return_rate']}%，检查产品描述准确性和尺码指南")
if d["conversion"] >= d["prev_conversion"] and d["bounce"] <= 55:
    st.success("核心指标健康，转化率和跳出率均在正常范围")
st.info("SKU-003（环保帆布袋）库存低于安全库存（当前 25，安全线 30），建议补货")

st.caption(f"数据范围: {period} | 更新: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
