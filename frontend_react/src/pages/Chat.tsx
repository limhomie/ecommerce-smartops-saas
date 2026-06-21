import { useState, useRef, useEffect, useCallback, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Input, Button, Typography, Card, Col, Row, Spin, Collapse, Empty, Tag } from 'antd'
import { SendOutlined, LoadingOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import client from '../api/client'
import ContextPanel from '../components/ContextPanel'
import { useBackgroundTask } from '../hooks/useBackgroundTask'
import { usePersistentMessages } from '../hooks/usePersistentMessages'

const { Title, Text, Paragraph } = Typography

const PRESETS = [
  '帮我分析上周转化率为什么下降',
  '为有机棉T恤生成Facebook广告脚本',
  '查询包裹 YT202506130001 的物流状态',
]

export default function Chat() {
  const { id } = useParams<{ id: string }>()
  const [_sessionId] = useState(id || localStorage.getItem('chat_session') || crypto.randomUUID())
  const sessionId = _sessionId
  const { messages, addMessage, updateLastAssistant } = usePersistentMessages(sessionId)
  const { status, result, progress, startTask } = useBackgroundTask(`chat_${sessionId}`)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  // Persist session id
  useEffect(() => { localStorage.setItem('chat_session', sessionId) }, [sessionId])

  // Handle task completion
  useEffect(() => {
    if (status === 'done' && result) {
      const report = (result.report as string) || ''
      updateLastAssistant(report || '任务完成')
    }
    if (status === 'error' && result) {
      updateLastAssistant('请求失败，请重试')
    }
  }, [status, result])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, progress])

  const loading = status === 'running'

  const userAnchors: { id: string; text: string }[] = []
  messages.forEach((m, i) => {
    if (m.role === 'user') userAnchors.push({ id: `chat_msg_${i}`, text: m.content.slice(0, 35) + (m.content.length > 35 ? '…' : '') })
  })

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return
    setInput('')
    addMessage({ role: 'user', content: text })
    addMessage({ role: 'assistant', content: '' })
    try {
      await client.post('/sessions', { title: text.slice(0, 50) })
    } catch { /* non-critical */ }
    startTask(text, sessionId)
  }, [loading, sessionId, addMessage, startTask])

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 120px)', maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={4} style={{ margin: 0 }}>Agent 对话</Title>
          {loading && <Tag color="processing" icon={<LoadingOutlined />}>后台执行中</Tag>}
        </div>

        <div style={{ flex: 1, overflow: 'auto', paddingRight: 8, marginBottom: 12 }}>
          {messages.length === 0 && !loading && (
            <Empty description="输入运营需求开始对话，或点击下方预设" style={{ marginTop: 60 }} />
          )}
          {messages.map((msg, i) => {
            const isUser = msg.role === 'user'
            const isEmpty = !isUser && !msg.content
            if (isEmpty && loading) {
              return (
                <Card key={i} size="small" style={{ marginBottom: 16, background: '#fffbe6', border: '1px solid #ffe58f', marginRight: 48 }}>
                  <Spin size="small" /> <Text style={{ marginLeft: 8 }}>Agent 正在后台执行... 可以切换页面，不会中断。</Text>
                  {progress.length > 0 && (
                    <Collapse style={{ marginTop: 8 }} ghost items={[{
                      key: 'prog', label: '实时进度',
                      children: progress.map((p, j) => <div key={j} style={{ fontSize: 12, color: '#666' }}>{p}</div>),
                    }]} />
                  )}
                </Card>
              )
            }
            if (isEmpty) return null
            return (
              <div key={i} style={{ marginBottom: 16 }}>
                {isUser && <div id={`chat_msg_${i}`} style={{ scrollMarginTop: 80 }} />}
                <Card size="small"
                  style={{
                    background: isUser ? '#e6f7ff' : '#fafafa',
                    border: isUser ? '1px solid #91d5ff' : '1px solid #e8e8e8',
                    marginLeft: isUser ? 48 : 0, marginRight: isUser ? 0 : 48,
                  }}
                  title={<Text strong style={{ fontSize: 13 }}>{isUser ? '👤 你' : '🤖 Agent'}</Text>}
                >
                  {isUser ? (
                    <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{msg.content}</Paragraph>
                  ) : (
                    <div style={{ fontSize: 14, lineHeight: 1.9 }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                  {msg.actions && msg.actions.length > 0 && (
                    <Collapse style={{ marginTop: 8 }} ghost items={[{
                      key: 'actions', label: `📋 行动建议 (${msg.actions.length}条)`,
                      children: <ul style={{ margin: 0, paddingLeft: 20 }}>{msg.actions.map((a, j) => <li key={j}>{a}</li>)}</ul>,
                    }]} />
                  )}
                </Card>
              </div>
            )
          })}
          <div ref={bottomRef} />
        </div>

        <Row gutter={8} style={{ marginBottom: 8 }}>
          {PRESETS.map(p => (
            <Col key={p}><Button size="small" onClick={() => sendMessage(p)} disabled={loading}>{p.slice(0, 18)}…</Button></Col>
          ))}
        </Row>

        <form onSubmit={(e: FormEvent) => { e.preventDefault(); sendMessage(input) }} style={{ display: 'flex', gap: 8 }}>
          <Input value={input} onChange={e => setInput(e.target.value)}
            placeholder="输入运营需求...（后台运行，切页面不中断）" disabled={loading} size="large" style={{ flex: 1 }} />
          <Button type="primary" htmlType="submit" loading={loading} icon={<SendOutlined />} size="large">发送</Button>
        </form>
      </div>
      <ContextPanel anchors={userAnchors} />
    </div>
  )
}
