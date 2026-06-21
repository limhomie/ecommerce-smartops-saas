import { useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Typography } from 'antd'
import { DashboardOutlined, MessageOutlined, EditOutlined, BookOutlined, FileTextOutlined, LogoutOutlined } from '@ant-design/icons'

const { Sider, Content } = AntLayout
const { Text } = Typography

const items = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/chat', icon: <MessageOutlined />, label: 'Agent 对话' },
  { key: '/content', icon: <EditOutlined />, label: '内容工厂' },
  { key: '/knowledge', icon: <BookOutlined />, label: '知识库' },
  { key: '/reports', icon: <FileTextOutlined />, label: '分析报告' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const nav = useNavigate()
  const loc = useLocation()
  const selected = '/' + (loc.pathname.split('/')[1] || '')

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={200} style={{ background: '#fff', borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: '20px 16px' }}>
          <Text strong style={{ fontSize: 15 }}>SmartOps Agent</Text>
        </div>
        <Menu mode="inline" selectedKeys={[selected]} items={items}
          onClick={({ key }) => nav(key)}
          style={{ borderRight: 0 }} />
        <div style={{ position: 'absolute', bottom: 24, width: '100%', padding: '0 16px' }}>
          <Menu mode="inline" items={[{
            key: 'logout', icon: <LogoutOutlined />, label: '退出登录',
          }]} onClick={() => { localStorage.removeItem('api_key'); nav('/login') }}
          style={{ borderRight: 0 }} />
        </div>
      </Sider>
      <Content style={{ padding: '24px 32px', background: '#f5f5f5', overflow: 'auto' }}>
        {children}
      </Content>
    </AntLayout>
  )
}
