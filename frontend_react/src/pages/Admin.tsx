import { useState, useEffect } from 'react'
import { Card, Button, Typography, Statistic, Row, Col, Space, Table, message } from 'antd'
import { SyncOutlined, ReloadOutlined } from '@ant-design/icons'
import client from '../api/client'

const { Title } = Typography

export default function Admin() {
  const [syncing, setSyncing] = useState(false)
  const [result, setResult] = useState<Record<string, number> | null>(null)
  const [entries, setEntries] = useState(0)
  const [users, setUsers] = useState<{ id: string; username: string; api_key: string; created_at: string }[]>([])
  const [tasks, setTasks] = useState(0)

  const loadStatus = async () => {
    try {
      const { data } = await client.get('/admin/sync/status')
      if (data.entries !== undefined) setEntries(data.entries)
    } catch { /* */ }
    try {
      const { data } = await client.get('/admin/users')
      if (data.users) setUsers(data.users)
    } catch { /* */ }
    try {
      const { data } = await client.get('/admin/stats')
      if (data.stats) setTasks(data.stats.total_tasks || tasks)
    } catch { /* */ }
  }

  const doSync = async () => {
    setSyncing(true); setResult(null)
    try {
      const { data } = await client.get('/admin/sync')
      const jobId = data.job_id
      const poll = async (): Promise<void> => {
        const { data: st } = await client.get(`/admin/sync/status/${jobId}`)
        if (st.status === 'done') { setResult(st.result); setSyncing(false); loadStatus(); return }
        if (st.status === 'not_found') throw new Error('job lost')
        await new Promise(r => setTimeout(r, 2000))
        return poll()
      }
      await poll()
    } catch { message.error('Sync failed'); setSyncing(false) }
  }

  useEffect(() => { loadStatus() }, [])

  const userColumns = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: 'API Key', dataIndex: 'api_key', key: 'api_key', render: (k: string) => <code>{k?.slice(0, 16)}...</code> },
    { title: '注册时间', dataIndex: 'created_at', key: 'created_at' },
  ]

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <Title level={4}>管理后台</Title>

      {/* Doc Sync */}
      <Card title="文档同步" style={{ marginBottom: 24 }}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col><Card size="small"><Statistic title="已跟踪文档" value={entries} suffix="个" /></Card></Col>
          <Col><Card size="small"><Statistic title="知识库块数" value={tasks} suffix="块" /></Card></Col>
        </Row>
        <Space>
          <Button type="primary" icon={<SyncOutlined />} loading={syncing} onClick={doSync}>立即同步</Button>
          <Button icon={<ReloadOutlined />} onClick={loadStatus}>刷新</Button>
        </Space>
        {result && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={6}><Statistic title="已创建" value={result.created || 0} valueStyle={{ color: '#3f8600' }} /></Col>
            <Col span={6}><Statistic title="已更新" value={result.updated || 0} valueStyle={{ color: '#faad14' }} /></Col>
            <Col span={6}><Statistic title="已删除" value={result.deleted || 0} valueStyle={{ color: '#cf1322' }} /></Col>
            <Col span={6}><Statistic title="未变化" value={result.unchanged || 0} /></Col>
          </Row>
        )}
      </Card>

      {/* User Management */}
      <Card title="用户管理" style={{ marginBottom: 24 }}>
        <Table dataSource={users} columns={userColumns} rowKey="id" size="small" pagination={false} />
      </Card>
    </div>
  )
}
