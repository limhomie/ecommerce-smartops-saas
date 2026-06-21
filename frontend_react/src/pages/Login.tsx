import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Input, Button, Typography, Space, message } from 'antd'
import client from '../api/client'

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [shownKey, setShownKey] = useState('')
  const nav = useNavigate()

  const handleRegister = async () => {
    try {
      const { data } = await client.post('/users/register', { username })
      setShownKey(data.user.api_key)
      message.success('注册成功！请保存你的 API Key')
    } catch {
      message.error('注册失败，用户名可能已被占用')
    }
  }

  const handleLogin = async () => {
    try {
      await client.get('/users/me', { headers: { 'X-API-Key': apiKey } })
      localStorage.setItem('api_key', apiKey)
      nav('/')
    } catch {
      message.error('API Key 无效')
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card style={{ width: 400 }}>
        <Typography.Title level={3} style={{ textAlign: 'center' }}>SmartOps Agent</Typography.Title>

        {mode === 'register' ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input placeholder="用户名（3-32 字符）" value={username}
              onChange={(e) => setUsername(e.target.value)} />
            <Button type="primary" block onClick={handleRegister}>注册</Button>
            {shownKey && (
              <Card size="small" style={{ background: '#f6ffed', marginTop: 12 }}>
                <Typography.Text strong>你的 API Key（仅显示一次）：</Typography.Text>
                <Typography.Paragraph copyable code style={{ marginTop: 8 }}>{shownKey}</Typography.Paragraph>
                <Button type="link" onClick={() => { setApiKey(shownKey); setMode('login') }}>
                  我已保存，去登录
                </Button>
              </Card>
            )}
            <Button type="link" block onClick={() => setMode('login')}>已有账号？登录</Button>
          </Space>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input.Password placeholder="粘贴 API Key" value={apiKey}
              onChange={(e) => setApiKey(e.target.value)} />
            <Button type="primary" block onClick={handleLogin}>登录</Button>
            <Button type="link" block onClick={() => setMode('register')}>没有账号？注册</Button>
          </Space>
        )}
      </Card>
    </div>
  )
}
