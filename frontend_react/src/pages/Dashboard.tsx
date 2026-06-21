import { useState, useMemo } from 'react'
import { Card, Row, Col, Select, Button, Typography, DatePicker } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { LineChart, Line, PieChart, Pie, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts'
import dayjs, { type Dayjs } from 'dayjs'

const { Title } = Typography
const { RangePicker } = DatePicker

const COLORS = ['#5B8FF9', '#5AD8A6', '#F6BD16', '#E8684A', '#6DC8EC']

type Period = '本周' | '上周' | '本月' | '上月' | '自定义'

interface Metrics {
  conversion: number; prev_conversion: number; aov: number; orders: number
  prev_orders: number; visitors: number; bounce: number; return_rate: number
  trend_labels: string[]; trend_current: number[]; trend_prev: number[]
  orders_daily: number[]; traffic: number[]
  sent_pos: number; sent_neu: number; sent_neg: number
  rating: number[]
}

function periodData(p: Period, start?: Dayjs, end?: Dayjs): Metrics {
  if (p === '自定义' && start && end) {
    const days = end.diff(start, 'day') + 1
    const labels = days <= 7
      ? ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].slice(0, days)
      : Array.from({length: Math.min(days, 7)}, (_, i) => `D${i + 1}`)
    const n = labels.length
    const gen = (base: number) => Array.from({length: n}, () => +(base + (Math.random() - 0.5) * base * 0.4).toFixed(1))
    const pct = () => +(60 + Math.random() * 20).toFixed(1)
    return {
      conversion: +pct().toFixed(1), prev_conversion: pct(), aov: +(30 + Math.random() * 30).toFixed(2),
      orders: Math.floor(200 + Math.random() * 2000), prev_orders: Math.floor(200 + Math.random() * 2000),
      visitors: Math.floor(8000 + Math.random() * 80000), bounce: Math.floor(30 + Math.random() * 40),
      return_rate: +(1 + Math.random() * 8).toFixed(1),
      trend_labels: labels, trend_current: gen(3.0), trend_prev: gen(3.2),
      orders_daily: gen(80).map(Math.floor), traffic: [35,28,16,12,9],
      sent_pos: Math.floor(55 + Math.random() * 25), sent_neu: Math.floor(15 + Math.random() * 15),
      sent_neg: Math.floor(5 + Math.random() * 10), rating: [45,28,15,7,5],
    }
  }
  if (p === '上周') return {
    conversion: 3.4, prev_conversion: 3.1, aov: 43.30, orders: 623, prev_orders: 580,
    visitors: 18320, bounce: 42, return_rate: 4.1,
    trend_labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    trend_current: [3.6,3.5,3.6,3.4,3.5,3.3,3.4],
    trend_prev: [3.3,3.2,3.1,3.0,3.1,3.2,3.1],
    orders_daily: [95,90,92,88,85,86,87], traffic: [38,25,15,14,8],
    sent_pos: 72, sent_neu: 20, sent_neg: 8, rating: [50,25,15,6,4],
  }
  if (p === '本月') return {
    conversion: 2.7, prev_conversion: 2.9, aov: 44.80, orders: 2150, prev_orders: 2300,
    visitors: 79600, bounce: 52, return_rate: 4.7,
    trend_labels: ['W1','W2','W3','W4'],
    trend_current: [3.1,2.8,2.9,2.1], trend_prev: [3.2,3.0,2.8,2.9],
    orders_daily: [580,560,540,470], traffic: [33,28,16,15,8],
    sent_pos: 68, sent_neu: 22, sent_neg: 10, rating: [45,28,15,7,5],
  }
  if (p === '上月') return {
    conversion: 2.9, prev_conversion: 3.2, aov: 43.90, orders: 2300, prev_orders: 2100,
    visitors: 79300, bounce: 49, return_rate: 4.3,
    trend_labels: ['W1','W2','W3','W4'],
    trend_current: [3.2,3.0,2.8,2.9], trend_prev: [3.1,3.3,3.0,2.7],
    orders_daily: [600,580,570,550], traffic: [35,30,17,12,6],
    sent_pos: 70, sent_neu: 21, sent_neg: 9, rating: [48,26,14,7,5],
  }
  return {
    conversion: 2.1, prev_conversion: 3.4, aov: 45.60, orders: 534, prev_orders: 623,
    visitors: 25430, bounce: 61, return_rate: 5.2,
    trend_labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    trend_current: [3.4,3.2,3.0,2.5,2.1,2.3,2.1],
    trend_prev: [3.6,3.5,3.6,3.4,3.5,3.3,3.4],
    orders_daily: [89,82,78,71,65,72,77], traffic: [30,35,18,10,7],
    sent_pos: 65, sent_neu: 25, sent_neg: 10, rating: [42,30,16,8,4],
  }
}

const cardStyle = { textAlign: 'center' as const }

export default function Dashboard() {
  const [period, setPeriod] = useState<Period>('本周')
  const [dates, setDates] = useState<[Dayjs, Dayjs] | null>(null)
  const [key, setKey] = useState(0)
  const today = dayjs()

  const displayLabel = useMemo(() => {
    if (period === '本周') return `${today.startOf('week').format('MM/DD')} — ${today.format('MM/DD')}`
    if (period === '上周') { const last = today.subtract(1, 'week'); return `${last.startOf('week').format('MM/DD')} — ${last.endOf('week').format('MM/DD')}` }
    if (period === '本月') return `${today.startOf('month').format('MM/DD')} — ${today.format('MM/DD')}`
    if (period === '上月') { const lm = today.subtract(1, 'month'); return `${lm.startOf('month').format('MM/DD')} — ${lm.endOf('month').format('MM/DD')}` }
    if (dates) return `${dates[0].format('MM/DD')} — ${dates[1].format('MM/DD')}`
    return ''
  }, [period, dates, today])

  const d = useMemo(() => periodData(period, dates?.[0], dates?.[1]), [period, dates, key])

  const diff = (v: number, prev: number) => {
    const pct = ((v - prev) / prev * 100).toFixed(1)
    const color = v >= prev ? '#2ecc71' : '#e74c3c'
    return <span style={{ color, fontSize: 12 }}>{v >= prev ? '↑' : '↓'}{pct}%</span>
  }

  const trendData = d.trend_labels.flatMap((l, i) => [
    { day: l, value: d.trend_current[i], type: '本期' },
    { day: l, value: d.trend_prev[i], type: '上期' },
  ])
  const trafficData = [
    { name: '自然搜索', value: d.traffic[0] },
    { name: '付费广告', value: d.traffic[1] },
    { name: '社交媒体', value: d.traffic[2] },
    { name: '直接访问', value: d.traffic[3] },
    { name: '邮件营销', value: d.traffic[4] },
  ]
  const funnelData = [
    { stage: '访客', value: d.visitors }, { stage: '商品页', value: 15200 },
    { stage: '加购', value: 3200 }, { stage: '结账', value: 1200 }, { stage: '下单', value: d.orders },
  ]
  const competitorData = [
    { brand: '我方', price: d.aov }, { brand: '竞品A', price: 29.99 },
    { brand: '竞品B', price: 34.99 }, { brand: '竞品C', price: 24.99 },
  ]
  const orderData = d.orders_daily.map((v, i) => ({ day: d.trend_labels[i], orders: v }))

  const chartHeight = 280

  return (
    <div style={{ paddingBottom: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Title level={4} style={{ margin: 0 }}>运营仪表盘</Title>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Select value={period} onChange={v => { setPeriod(v); setDates(null) }} style={{ width: 90 }}
            options={['本周','上周','本月','上月','自定义'].map(v => ({ value: v, label: v }))} />
          {period === '自定义' && <RangePicker value={dates as [Dayjs, Dayjs]} onChange={v => setDates(v ? [v[0]!, v[1]!] : null)} style={{ width: 240 }} />}
          {(period !== '自定义' || dates) && <span style={{ color: '#999', fontSize: 12 }}>{displayLabel}</span>}
          <Button icon={<ReloadOutlined />} onClick={() => setKey(k => k + 1)} />
        </div>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}><Card style={cardStyle}><div style={{ color: '#999', fontSize: 12 }}>转化率</div><div style={{ fontSize: 28, fontWeight: 700 }}>{d.conversion}%</div>{diff(d.conversion, d.prev_conversion)}</Card></Col>
        <Col xs={12} sm={6}><Card style={cardStyle}><div style={{ color: '#999', fontSize: 12 }}>订单量</div><div style={{ fontSize: 28, fontWeight: 700 }}>{d.orders.toLocaleString()}</div>{diff(d.orders, d.prev_orders)}</Card></Col>
        <Col xs={12} sm={6}><Card style={cardStyle}><div style={{ color: '#999', fontSize: 12 }}>客单价</div><div style={{ fontSize: 28, fontWeight: 700 }}>${d.aov.toFixed(2)}</div></Card></Col>
        <Col xs={12} sm={6}><Card style={cardStyle}><div style={{ color: '#999', fontSize: 12 }}>访客数</div><div style={{ fontSize: 28, fontWeight: 700 }}>{d.visitors.toLocaleString()}</div></Card></Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="转化率趋势对比" size="small">
            <ResponsiveContainer width="100%" height={chartHeight}>
              <LineChart data={trendData}><XAxis dataKey="day" fontSize={12} /><YAxis fontSize={12} /><Tooltip /><Legend /><Line type="monotone" dataKey="value" stroke="#5B8FF9" name="本期" /><Line type="monotone" dataKey="value" stroke="#F6BD16" name="上期" /></LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="流量来源分布" size="small">
            <ResponsiveContainer width="100%" height={chartHeight}>
              <PieChart><Pie data={trafficData} dataKey="value" nameKey="name" outerRadius={100} label>{trafficData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="竞品价格对比" size="small">
            <ResponsiveContainer width="100%" height={chartHeight}>
              <BarChart data={competitorData}><XAxis dataKey="brand" fontSize={12} /><YAxis fontSize={12} /><Tooltip /><Bar dataKey="price" fill="#5B8FF9" name="价格(USD)" /></BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={`每日订单量 (共${d.orders}单)`} size="small">
            <ResponsiveContainer width="100%" height={chartHeight}>
              <BarChart data={orderData}><XAxis dataKey="day" fontSize={12} /><YAxis fontSize={12} /><Tooltip /><Bar dataKey="orders" fill="#5AD8A6" name="订单" /></BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="转化漏斗" size="small">
            <ResponsiveContainer width="100%" height={chartHeight}>
              <BarChart data={funnelData} layout="vertical"><XAxis type="number" fontSize={12} /><YAxis dataKey="stage" type="category" fontSize={12} /><Tooltip /><Bar dataKey="value" fill="#6DC8EC" name="人数" /></BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={`正面舆情占比 (${d.sent_pos}%)`} size="small">
            <ResponsiveContainer width="100%" height={chartHeight}>
              <PieChart><Pie data={[{name:'正面',value:d.sent_pos},{name:'中性',value:d.sent_neu},{name:'负面',value:d.sent_neg}]} dataKey="value" innerRadius={60} outerRadius={100}>{[<Cell key={0} fill="#5AD8A6" />,<Cell key={1} fill="#F6BD16" />,<Cell key={2} fill="#E8684A" />]}</Pie><Tooltip /><Legend /></PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
