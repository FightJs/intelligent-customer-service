import { HashRouter, NavLink } from 'react-router-dom'
import App from './App'
import { AuthProvider, useAuth } from './state/AuthContext'
import './styles/pagesDemo.css'

function DemoNav() {
  const { user } = useAuth()
  return <header className="pages-demo-bar">
    <p><strong>流程演示</strong> · 使用合成数据与固定媒体样张，输入仅留在当前浏览器标签页。请使用虚构信息。</p>
    <nav aria-label="演示页面">
      <NavLink end to="/">产品介绍</NavLink>
      <NavLink to="/welcome">开场页</NavLink>
      <NavLink to="/workbench-preview">租赁预览</NavLink>
      <NavLink to={user ? '/workbench' : '/login'}>开始体验</NavLink>
      {user && <><NavLink to="/plans">我的方案</NavLink><NavLink to="/admin">管理后台</NavLink></>}
    </nav>
  </header>
}

export default function PagesDemo() {
  return <HashRouter><AuthProvider>
    <div className="pages-demo">
      <DemoNav />
      <div className="pages-demo-app"><App /></div>
    </div>
  </AuthProvider></HashRouter>
}
