import { useState, useMemo, useEffect, useRef } from 'react'
import { Card, Input, Select, Button, Typography, Tabs, Spin, Empty, Divider, Row, Col, Tag } from 'antd'
import { SendOutlined, LoadingOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import client from '../api/client'

const { Title, Text } = Typography

const AUDIENCE_PRESETS = ['年轻女性', '商务人士', '学生', '户外爱好者', '宝妈', 'Z世代', '银发族']
const TONE_PRESETS = ['专业正式', '活泼轻松', '情感共鸣', '科技感', '极简风', '可爱风']
const TYPE_OPTIONS = [
  'A+ 详情页文案', 'SEO 关键词', 'Facebook 广告脚本',
  'Instagram 广告脚本', '邮件营销文案', '产品标题优化',
  '品牌故事', '卖点提炼', '小红书笔记',
]

const STORAGE_KEY = 'content_factory_task'

function loadTaskId(): string | null {
  try { return localStorage.getItem(STORAGE_KEY) } catch { return null }
}
function saveTaskId(id: string) { try { localStorage.setItem(STORAGE_KEY, id) } catch { /* */ } }
function clearTaskId() { try { localStorage.removeItem(STORAGE_KEY) } catch { /* */ } }

export default function ContentFactory() {
  const [product, setProduct] = useState('有机棉T恤')
  const [audiencePresets, setAudiencePresets] = useState<string[]>(['年轻女性'])
  const [audienceCustom, setAudienceCustom] = useState('')
  const [tonePreset, setTonePreset] = useState('专业正式')
  const [toneCustom, setToneCustom] = useState('')
  const [types, setTypes] = useState<string[]>(['A+ 详情页文案', 'SEO 关键词', 'Facebook 广告脚本'])
  const [typeCustom, setTypeCustom] = useState('')
  const [loading, setLoading] = useState(false)
  const [generated, setGenerated] = useState('')
  const polling = useRef(false)

  // Resume background task on mount OR when loading starts
  const [taskId, setTaskId] = useState<string | null>(loadTaskId)

  useEffect(() => {
    const tid = taskId || loadTaskId()
    if (!tid || tid === 'undefined' || polling.current) return
    polling.current = true
    setLoading(true)
    let cancelled = false
    const poll = async () => {
      while (!cancelled) {
        try {
          const { data } = await client.get(`/content/tasks/${tid}`)
          if (cancelled) return
          if (data.status === 'completed') {
            setGenerated(data.result?.generated || data.result?.report || '')
            setLoading(false)
            clearTaskId()
            setTaskId(null)
            return
          }
          if (data.status === 'failed') {
            setGenerated('生成失败，请重试')
            setLoading(false)
            clearTaskId()
            setTaskId(null)
            return
          }
        } catch { /* retry */ }
        await new Promise(r => setTimeout(r, 1500))
      }
    }
    poll()
    return () => { cancelled = true; polling.current = false }
  }, [taskId])

  const tone = tonePreset === '自定义' ? toneCustom : tonePreset
  const audience = useMemo(() => {
    const parts = [...audiencePresets]
    if (audienceCustom) parts.push(audienceCustom)
    return parts.join('、')
  }, [audiencePresets, audienceCustom])
  const allTypes = useMemo(() => [...types, ...(typeCustom ? [typeCustom] : [])], [types, typeCustom])

  const canGenerate = product && audience && allTypes.length > 0 && !loading

  const generate = async () => {
    setLoading(true); setGenerated('')
    const typesStr = allTypes.map(t => `- ${t}`).join('\n')
    const prompt = `你是一位顶级电商文案和广告创意专家。

## 产品信息
- 产品名称：${product}
- 目标人群：${audience}
- 文案风格：${tone}

## 需要生成的内容类型
${typesStr}

## 要求
1. 每种内容类型都要单独输出，用「## 类型名称」作为标题
2. 文案必须符合指定风格，精准针对目标人群
3. SEO关键词要区分主关键词和长尾关键词
4. 广告脚本要包含标题、正文、CTA，至少两个版本
5. 直接输出可发布内容，用中文`
    try {
      const { data } = await client.post('/content/generate', { product, audience, tone, types: allTypes, prompt })
      if (data.task_id) { saveTaskId(data.task_id); setTaskId(data.task_id) }
    } catch {
      setLoading(false)
      setGenerated('请求失败，请重试')
    }
  }

  const sections = useMemo(() => {
    if (!generated) return []
    return generated.split(/\n(?=## )/).filter(Boolean)
  }, [generated])

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>AI 内容工厂</Title>
        {loading && <Tag color="processing" icon={<LoadingOutlined />}>后台生成中</Tag>}
      </div>

      <Row gutter={24} style={{ marginTop: 16 }}>
        <Col xs={24} lg={10}>
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Text strong>产品信息</Text>
              <Input value={product} onChange={e => setProduct(e.target.value)} placeholder="产品名称" style={{ marginTop: 4 }} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>目标人群</Text>
              <Select mode="multiple" value={audiencePresets} onChange={setAudiencePresets}
                options={AUDIENCE_PRESETS.map(v => ({ value: v, label: v }))} style={{ width: '100%', marginTop: 4 }} />
              <Input value={audienceCustom} onChange={e => setAudienceCustom(e.target.value)}
                placeholder="自定义人群描述" style={{ marginTop: 8 }} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>文案风格</Text>
              <Select value={tonePreset} onChange={setTonePreset}
                options={[...TONE_PRESETS, '自定义'].map(v => ({ value: v, label: v }))} style={{ width: '100%', marginTop: 4 }} />
              {tonePreset === '自定义' && (
                <Input value={toneCustom} onChange={e => setToneCustom(e.target.value)}
                  placeholder="例：小红书种草风格，多用emoji" style={{ marginTop: 8 }} />
              )}
            </div>
            <Divider style={{ margin: '12px 0' }} />
            <div style={{ marginBottom: 16 }}>
              <Text strong>生成内容类型</Text>
              <Select mode="multiple" value={types} onChange={setTypes}
                options={TYPE_OPTIONS.map(v => ({ value: v, label: v }))} style={{ width: '100%', marginTop: 4 }} />
              <Input value={typeCustom} onChange={e => setTypeCustom(e.target.value)}
                placeholder="自定义内容类型" style={{ marginTop: 8 }} />
            </div>
            <Button type="primary" size="large" block loading={loading}
              disabled={!canGenerate} icon={<SendOutlined />} onClick={generate}>
              🚀 AI 生成内容
            </Button>
            {generated && !loading && (
              <Button size="small" style={{ marginTop: 8 }} onClick={() => { setGenerated(''); clearTaskId() }}>重新生成</Button>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card title="生成结果" style={{ minHeight: 400 }}>
            {loading && !generated && (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" />
                <div style={{ marginTop: 12 }}><Text type="secondary">AI 正在后台生成内容... 可切换页面，不会中断。</Text></div>
              </div>
            )}
            {!loading && !generated && <Empty description="输入产品信息后点击「AI 生成内容」" />}
            {generated && sections.length > 1 && (
              <Tabs items={sections.map((sec, i) => {
                const title = sec.match(/^##\s*(.+)/)?.[1] || `第${i + 1}部分`
                return { key: String(i), label: title.slice(0, 20), children: <ReactMarkdown remarkPlugins={[remarkGfm]}>{sec}</ReactMarkdown> }
              })} />
            )}
            {generated && sections.length <= 1 && <ReactMarkdown remarkPlugins={[remarkGfm]}>{generated}</ReactMarkdown>}
            {loading && generated && (
              <div style={{ textAlign: 'center', padding: 20 }}><Spin /> <Text type="secondary">继续生成中...</Text></div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
