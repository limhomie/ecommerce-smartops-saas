"""Chart generation utilities — create Plotly chart specs from agent data.

Charts are stored as Plotly JSON specs that can be rendered by Streamlit's
st.plotly_chart() or any Plotly-compatible frontend.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import plotly.express as px


def conversion_trend_chart(data: dict | None = None) -> dict:
    """Line chart: conversion rate trend over 7 days."""
    if data is None:
        data = {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "current": [3.4, 3.2, 3.0, 2.5, 2.1, 2.3, 2.1],
            "previous": [3.6, 3.5, 3.6, 3.4, 3.5, 3.3, 3.4],
        }

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["labels"], y=data["current"],
        mode="lines+markers", name="本周",
        line=dict(color="#e74c3c", width=3),
        marker=dict(size=8),
    ))
    fig.add_trace(go.Scatter(
        x=data["labels"], y=data["previous"],
        mode="lines+markers", name="上周",
        line=dict(color="#95a5a6", width=2, dash="dash"),
        marker=dict(size=6),
    ))
    fig.update_layout(
        title="转化率趋势对比",
        xaxis_title="",
        yaxis_title="转化率 (%)",
        template="plotly_white",
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig.to_dict()


def traffic_source_pie(data: dict | None = None) -> dict:
    """Pie chart: traffic source breakdown."""
    if data is None:
        data = {
            "labels": ["自然搜索", "付费广告", "社交媒体", "直接访问", "邮件营销"],
            "values": [35, 30, 15, 12, 8],
        }

    fig = go.Figure(data=[go.Pie(
        labels=data["labels"],
        values=data["values"],
        hole=0.4,
        marker=dict(colors=["#2ecc71", "#e74c3c", "#3498db", "#f39c12", "#9b59b6"]),
        textinfo="label+percent",
    )])
    fig.update_layout(
        title="流量来源分布",
        template="plotly_white",
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig.to_dict()


def conversion_funnel(data: dict | None = None) -> dict:
    """Funnel chart: conversion funnel stages."""
    if data is None:
        data = {
            "stages": ["访客", "商品页浏览", "加购", "发起结账", "下单"],
            "values": [25430, 15200, 3200, 1200, 534],
            "rates": ["100%", "59.8%", "12.6%", "4.7%", "2.1%"],
        }

    fig = go.Figure(data=[go.Funnel(
        y=data["stages"],
        x=data["values"],
        textposition="inside",
        texttemplate="%{value:,}<br>%{text}",
        text=[f"{r}" for r in data["rates"]],
        marker=dict(color=["#3498db", "#2ecc71", "#f39c12", "#e67e22", "#e74c3c"]),
    )])
    fig.update_layout(
        title="转化漏斗",
        template="plotly_white",
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig.to_dict()


def competitor_price_chart(data: dict | None = None) -> dict:
    """Bar chart: competitor price comparison."""
    if data is None:
        data = {
            "competitors": ["我方", "竞品A", "竞品B", "竞品C"],
            "prices": [45.60, 29.99, 34.99, 24.99],
            "ratings": [4.6, 4.2, 4.5, 3.8],
        }

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=data["competitors"], y=data["prices"],
        name="价格 ($)",
        marker=dict(color=["#2ecc71", "#e74c3c", "#f39c12", "#95a5a6"]),
        text=[f"${p}" for p in data["prices"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="竞品价格对比",
        xaxis_title="",
        yaxis_title="价格 ($)",
        template="plotly_white",
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig.to_dict()


def order_trend_bar(data: dict | None = None) -> dict:
    """Bar chart: daily order volume."""
    if data is None:
        data = {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "values": [89, 82, 78, 71, 65, 72, 77],
        }

    fig = go.Figure(data=[go.Bar(
        x=data["labels"], y=data["values"],
        marker=dict(
            color=data["values"],
            colorscale="Viridis",
            showscale=False,
        ),
        text=data["values"],
        textposition="outside",
    )])
    fig.update_layout(
        title="本周每日订单量",
        xaxis_title="",
        yaxis_title="订单数",
        template="plotly_white",
        height=350,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig.to_dict()


def sentiment_gauge(positive: float = 65, neutral: float = 25, negative: float = 10) -> dict:
    """Gauge-like indicator for sentiment overview."""
    fig = go.Figure(data=[go.Indicator(
        mode="gauge+number+delta",
        value=positive,
        title={"text": "正面舆情占比 (%)"},
        delta={"reference": 72, "decreasing": {"color": "red"}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#2ecc71"},
            "steps": [
                {"range": [0, 40], "color": "#ff7675"},
                {"range": [40, 70], "color": "#ffeaa7"},
                {"range": [70, 100], "color": "#55efc4"},
            ],
            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 70},
        },
    )])
    fig.update_layout(
        template="plotly_white",
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig.to_dict()


def rating_distribution(data: dict | None = None) -> dict:
    """Horizontal bar: rating distribution."""
    if data is None:
        data = {
            "ratings": ["5星", "4星", "3星", "2星", "1星"],
            "percentages": [45, 28, 15, 7, 5],
        }

    fig = go.Figure(data=[go.Bar(
        y=data["ratings"],
        x=data["percentages"],
        orientation="h",
        marker=dict(
            color=data["percentages"],
            colorscale="RdYlGn",
            showscale=False,
        ),
        text=[f"{p}%" for p in data["percentages"]],
        textposition="outside",
    )])
    fig.update_layout(
        title="用户评分分布",
        xaxis_title="占比 (%)",
        yaxis_title="",
        template="plotly_white",
        height=300,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig.to_dict()


# ── Chart registry for easy lookup ──

CHART_GENERATORS: dict[str, callable] = {
    "conversion_trend": conversion_trend_chart,
    "traffic_source": traffic_source_pie,
    "conversion_funnel": conversion_funnel,
    "competitor_price": competitor_price_chart,
    "order_trend": order_trend_bar,
    "sentiment_gauge": sentiment_gauge,
    "rating_distribution": rating_distribution,
}


def get_charts_for_analysis(context: dict) -> list[dict]:
    """Given analysis context, return relevant chart specs.

    Args:
        context: dict with keys like 'has_conversion', 'has_competitor', etc.

    Returns:
        List of Plotly figure dicts ready for st.plotly_chart()
    """
    charts = []
    if context.get("has_conversion"):
        charts.append(conversion_trend_chart())
        charts.append(conversion_funnel())
        charts.append(traffic_source_pie())
    if context.get("has_competitor"):
        charts.append(competitor_price_chart())
    if context.get("has_sentiment"):
        charts.append(sentiment_gauge())
        charts.append(rating_distribution())
    if context.get("has_orders"):
        charts.append(order_trend_bar())
    return charts
