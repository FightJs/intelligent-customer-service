import { useState } from 'react'
import AdminHeader from '../components/admin/AdminHeader'
import DeliveriesTab from './admin/DeliveriesTab'
import UsersTab from './admin/UsersTab'

type Tab = 'deliveries' | 'users'

/** 管理后台编排层：顶栏 tab 切换 + 内容区。各 tab 自管理数据与状态。 */
export default function AdminScreen() {
  const [tab, setTab] = useState<Tab>('deliveries')

  return (
    <div className="flex h-full flex-col bg-base text-primary">
      <AdminHeader tab={tab} onTabChange={setTab} />
      <main className="flex-1 overflow-auto p-5">
        {tab === 'deliveries' ? <DeliveriesTab /> : <UsersTab />}
      </main>
    </div>
  )
}
