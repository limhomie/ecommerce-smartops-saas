import { useState } from 'react'
import { Card, Input, Button, Upload, Typography, List, message, Tabs, Statistic, Row, Col, Divider, Select, Space } from 'antd'
import { SearchOutlined, InboxOutlined } from '@ant-design/icons'
import client from '../api/client'

const { Title, Text, Paragraph } = Typography
const { Dragger } = Upload

const COLLECTIONS = ['products', 'competitors', 'ads_history', 'policies', 'enterprise_wiki']
const COLLECTION_LABELS: Record<string, string> = {
  products: '产品信息', competitors: '竞品数据', ads_history: '广告历史',
  policies: '政策FAQ', enterprise_wiki: '企业知识库',
}

export default function KnowledgeBase() {
  // search
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<{ content: string; distance: number; metadata?: { collection?: string } }[]>([])
  const [searching, setSearching] = useState(false)

  // upload
  const [targetColl, setTargetColl] = useState('products')
  const [pasteText, setPasteText] = useState('')
  const [pasteColl, setPasteColl] = useState('products')
  const [uploading, setUploading] = useState(false)

  // stats
  const [stats, setStats] = useState<Record<string, number>>({})

  const search = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const { data } = await client.get('/knowledge/search', { params: { q: query } })
      setResults(data.docs || [])
    } catch { message.error('搜索失败') }
    finally { setSearching(false) }
  }

  const uploadFile = async (file: File) => {
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('collection', targetColl)

      const { data } = await client.post('/knowledge/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      if (data.status === 'duplicate') {
        message.warning(data.message || '内容已存在，跳过重复录入')
      } else {
        message.success(`${file.name} 已上传，切分为 ${data.chunks} 个向量块 → ${targetColl}`)
      }
      loadStats()
    } catch { message.error('上传失败') }
    finally { setUploading(false) }
  }

  const pasteSubmit = async () => {
    if (!pasteText.trim()) return
    try {
      const { data } = await client.post('/knowledge/documents', { content: pasteText, collection: pasteColl,
        metadata: { source: 'manual_paste' } })
      if (data.status === 'duplicate') {
        message.warning(data.message || '内容已存在，跳过重复录入')
      } else {
        message.success(`已入库，${data.chunks} 个向量块 → ${pasteColl}`)
      }
      setPasteText('')
      loadStats()
    } catch { message.error('入库失败') }
  }

  const loadStats = async () => {
    try {
      const { data } = await client.get('/knowledge/search', { params: { q: '__stats__' } })
      if (data.stats) setStats(data.stats)
    } catch { /* stats not critical */ }
  }

  const tabItems = [
    {
      key: 'upload', label: '📤 上传文档',
      children: (
        <div>
          <Row gutter={16}>
            <Col xs={24} md={16}>
              <Dragger accept=".md,.txt,.html,.pdf" showUploadList={false}
                customRequest={({ file }) => uploadFile(file as File)}>
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p>点击或拖拽文件上传（.md / .txt / .html / .pdf）</p>
              </Dragger>
            </Col>
            <Col xs={24} md={8}>
              <Select value={targetColl} onChange={setTargetColl} style={{ width: '100%', marginTop: 16 }}
                options={COLLECTIONS.map(c => ({ value: c, label: COLLECTION_LABELS[c] || c }))} />
              <Text type="secondary" style={{ fontSize: 12 }}>选择目标知识库</Text>
            </Col>
          </Row>

          <Divider>或直接粘贴</Divider>
          <Input.TextArea rows={4} value={pasteText} onChange={e => setPasteText(e.target.value)}
            placeholder="直接粘贴需要入库的政策、文档、竞品信息..." />
          <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
            <Select value={pasteColl} onChange={setPasteColl} style={{ width: 160 }}
              options={COLLECTIONS.map(c => ({ value: c, label: COLLECTION_LABELS[c] || c }))} />
            <Button type="primary" onClick={pasteSubmit} disabled={!pasteText.trim()} loading={uploading}>📋 粘贴入库</Button>
          </div>
        </div>
      ),
    },
    {
      key: 'search', label: '🔍 语义搜索',
      children: (
        <div>
          <Space.Compact style={{ width: '100%' }}>
            <Input prefix={<SearchOutlined />} size="large" value={query}
              onChange={e => setQuery(e.target.value)} onPressEnter={search}
              placeholder="输入自然语言搜索知识库..." />
            <Button type="primary" size="large" loading={searching} onClick={search}>搜索</Button>
          </Space.Compact>
          {results.length > 0 && (
            <List style={{ marginTop: 16 }} dataSource={results}
              renderItem={(item) => (
                <List.Item>
                  <Card size="small" style={{ width: '100%' }}
                    title={<Text type="secondary" style={{ fontSize: 12 }}>来源: {item.metadata?.collection || 'unknown'} | 距离: {item.distance.toFixed(3)}</Text>}>
                    <Paragraph ellipsis={{ rows: 5 }} style={{ margin: 0, fontSize: 13 }}>{item.content}</Paragraph>
                  </Card>
                </List.Item>
              )} />
          )}
        </div>
      ),
    },
    {
      key: 'stats', label: '📊 统计概览',
      children: (
        <Row gutter={16}>
          {COLLECTIONS.map(c => (
            <Col xs={12} sm={8} md={4} key={c}>
              <Card size="small" style={{ textAlign: 'center' }}>
                <Statistic title={COLLECTION_LABELS[c] || c} value={stats[c] || 0} suffix="块" />
              </Card>
            </Col>
          ))}
          <Col span={24} style={{ marginTop: 16 }}>
            <Button onClick={loadStats}>刷新统计</Button>
          </Col>
        </Row>
      ),
    },
  ]

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <Title level={4}>知识库管理</Title>
      <Tabs items={tabItems} />
    </div>
  )
}
