import { useState } from 'react'
import { Card, Select, Typography, Button, Space, Spin, Empty, Row, Col, DatePicker, Tag } from 'antd'
import { FileTextOutlined, LoadingOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Line, Pie, Funnel, Bar, Gauge } from '@ant-design/charts'
import type { Dayjs } from 'dayjs'
import client from '../api/client'
import { useBackgroundTask, clearBackgroundTask } from '../hooks/useBackgroundTask'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const REPORT_TYPES = ['转化率诊断报告', '竞品分析报告', '广告效果报告', '舆情分析报告', '综合运营周报']
const PERIODS = ['本周', '上周', '本月']

interface ReportData {
  conversion: number; prev_conversion: number; aov: number; orders: number
  visitors: number; bounce: number; return_rate: number
  trend_labels: string[]; trend_current: number[]; trend_prev: number[]
  orders_daily: number[]; traffic: number[]
  sent_pos: number; sent_neu: number; sent_neg: number
  rating: number[]
}

const PERIOD_DATA: Record<string, ReportData> = {
  '本周': { conversion: 2.1, prev_conversion: 3.4, aov: 45.60, orders: 534, visitors: 25430, bounce: 61, return_rate: 5.2,
    trend_labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    trend_current: [3.4,3.2,3.0,2.5,2.1,2.3,2.1], trend_prev: [3.6,3.5,3.6,3.4,3.5,3.3,3.4],
    orders_daily: [89,82,78,71,65,72,77], traffic: [30,35,18,10,7],
    sent_pos: 65, sent_neu: 25, sent_neg: 10, rating: [42,30,16,8,4] },
  '上周': { conversion: 3.4, prev_conversion: 3.1, aov: 43.30, orders: 623, visitors: 18320, bounce: 42, return_rate: 4.1,
    trend_labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    trend_current: [3.6,3.5,3.6,3.4,3.5,3.3,3.4], trend_prev: [3.3,3.2,3.1,3.0,3.1,3.2,3.1],
    orders_daily: [95,90,92,88,85,86,87], traffic: [38,25,15,14,8],
    sent_pos: 72, sent_neu: 20, sent_neg: 8, rating: [50,25,15,6,4] },
  '本月': { conversion: 2.7, prev_conversion: 2.9, aov: 44.80, orders: 2150, visitors: 79600, bounce: 52, return_rate: 4.7,
    trend_labels: ['W1','W2','W3','W4'],
    trend_current: [3.1,2.8,2.9,2.1], trend_prev: [3.2,3.0,2.8,2.9],
    orders_daily: [580,560,540,470], traffic: [33,28,16,15,8],
    sent_pos: 68, sent_neu: 22, sent_neg: 10, rating: [45,28,15,7,5] },
}

const AD_DATA = { campaigns: ['夏季特惠','新品首发','品牌种草','会员日','清仓'], roas: [3.2,2.8,2.1,2.5,1.6] }

const TASK_KEY = 'report_generator'

export default function Reports() {
  const [reportType, setReportType] = useState(REPORT_TYPES[0])
  const [period, setPeriod] = useState(PERIODS[0])
  const [dates, setDates] = useState<[Dayjs, Dayjs] | null>(null)

  const { status, result, startTask, clear } = useBackgroundTask(TASK_KEY)
  const loading = status === 'running'
  const report = (result?.report as string) || ''
  const actions = (result?.action_items as string[]) || []

  const chartHeight = 260
  const d = PERIOD_DATA[period] || PERIOD_DATA['本周']
  const trendData = d.trend_labels.flatMap((l, i) => [
    { day: l, value: d.trend_current[i], type: '本期' },
    { day: l, value: d.trend_prev[i], type: '上期' },
  ])

  const generate = async () => {
    const range = dates ? `${dates[0].format('MM/DD')}-${dates[1].format('MM/DD')}` : period
    try { await client.post('/sessions', { title: `${reportType} ${range}` }) } catch { /* ok */ }
    startTask(`生成${reportType}，时间范围：${range}`)
  }

  const handleClear = () => { clear(); clearBackgroundTask(TASK_KEY) }

  const isConversion = reportType === '转化率诊断报告'
  const isCompetitor = reportType === '竞品分析报告'
  const isAd = reportType === '广告效果报告'
  const isSentiment = reportType === '舆情分析报告'
  const isWeekly = reportType === '综合运营周报'

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>分析报告</Title>
        {loading && <Tag color="processing" icon={<LoadingOutlined />}>后台生成中</Tag>}
      </div>

      <Card style={{ marginBottom: 24 }}>
        <Space wrap>
          <Select value={reportType} onChange={v => { setReportType(v); handleClear() }} style={{ width: 180 }}
            options={REPORT_TYPES.map(v => ({ value: v, label: v }))} />
          <Select value={period} onChange={v => { setPeriod(v); setDates(null) }} style={{ width: 100 }}
            options={[...PERIODS, '自定义'].map(v => ({ value: v, label: v }))} />
          {period === '自定义' && (
            <RangePicker value={dates as [Dayjs, Dayjs]} onChange={v => setDates(v ? [v[0]!, v[1]!] : null)} style={{ width: 240 }} />
          )}
          <Button type="primary" loading={loading} icon={<FileTextOutlined />} onClick={generate}>生成报告</Button>
          {status === 'done' && <Button size="small" onClick={handleClear}>重新生成</Button>}
        </Space>
      </Card>

      {loading && <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /><div style={{ marginTop: 16 }}><Text type="secondary">AI 正在撰写报告... 可切换页面，不会中断。</Text></div></div>}
      {!loading && !report && <Empty description="选择报告类型和时间范围，点击生成" />}

      {report && !loading && (
        <div>
          {(isConversion || isWeekly) && (
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col xs={24} lg={12}><Card size="small" title="转化率趋势"><Line data={trendData} xField="day" yField="value" colorField="type" height={chartHeight} /></Card></Col>
              <Col xs={24} lg={12}><Card size="small" title="转化漏斗"><Funnel data={[
                { stage: '访客', value: d.visitors }, { stage: '商品页', value: 15200 },
                { stage: '加购', value: 3200 }, { stage: '结账', value: 1200 }, { stage: '下单', value: d.orders },
              ]} xField="stage" yField="value" height={chartHeight} /></Card></Col>
              <Col xs={24} lg={12}><Card size="small" title="流量来源"><Pie data={[
                { type: '自然搜索', value: d.traffic[0] }, { type: '付费广告', value: d.traffic[1] },
                { type: '社交媒体', value: d.traffic[2] }, { type: '直接访问', value: d.traffic[3] },
                { type: '邮件营销', value: d.traffic[4] },
              ]} angleField="value" colorField="type" innerRadius={0.4} height={chartHeight} /></Card></Col>
              <Col xs={24} lg={12}><Card size="small" title="每日订单"><Bar data={d.orders_daily.map((v, i) => ({ day: d.trend_labels[i], orders: v }))} xField="day" yField="orders" height={chartHeight} /></Card></Col>
            </Row>
          )}
          {(isCompetitor || isWeekly) && (
            <Card size="small" title="竞品价格对比" style={{ marginBottom: 16 }}>
              <Bar data={[{ brand: '我方', price: d.aov }, { brand: '竞品A', price: 29.99 }, { brand: '竞品B', price: 34.99 }, { brand: '竞品C', price: 24.99 }]} xField="brand" yField="price" height={chartHeight} />
            </Card>
          )}
          {(isAd || isWeekly) && (
            <Card size="small" title="广告系列 ROAS 对比" style={{ marginBottom: 16 }}>
              <Bar data={AD_DATA.campaigns.map((c, i) => ({ campaign: c, roas: AD_DATA.roas[i] }))} xField="campaign" yField="roas" height={chartHeight} />
            </Card>
          )}
          {(isSentiment || isWeekly) && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col xs={24} lg={12}><Card size="small" title={`正面舆情 ${d.sent_pos}%`}><Gauge percent={d.sent_pos / 100} height={chartHeight} /></Card></Col>
              <Col xs={24} lg={12}><Card size="small" title="评分分布"><Bar data={[
                { rating: '5星', pct: d.rating[0] }, { rating: '4星', pct: d.rating[1] },
                { rating: '3星', pct: d.rating[2] }, { rating: '2星', pct: d.rating[3] },
                { rating: '1星', pct: d.rating[4] },
              ]} xField="rating" yField="pct" height={chartHeight} /></Card></Col>
            </Row>
          )}
          <Card style={{ marginTop: 16 }}>
            <div style={{ fontSize: 14, lineHeight: 2 }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
            </div>
          </Card>
          {actions.length > 0 && (
            <Card style={{ marginTop: 16 }} title="📋 行动建议">
              <ul style={{ margin: 0, paddingLeft: 20 }}>{actions.map((a, i) => <li key={i} style={{ marginBottom: 4 }}>{a}</li>)}</ul>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
