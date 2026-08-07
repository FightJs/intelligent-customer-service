import { useEffect, useRef, useState } from 'react'
import AdminHeader from '../components/admin/AdminHeader'
import AdminErrorNotification from '../components/admin/AdminErrorNotification'
import DeliveriesTab from './admin/DeliveriesTab'
import UsersTab from './admin/UsersTab'

type Tab = 'deliveries' | 'users'

/** 管理后台编排层：顶栏 tab 切换 + 内容区。各 tab 自管理数据与状态。 */
export default function AdminScreen() {
  const [tab, setTab] = useState<Tab>('deliveries')
  const [deliveryUserId, setDeliveryUserId] = useState<number | undefined>()
  const [unsupportedDocumentVisible, setUnsupportedDocumentVisible] = useState(false)
  const [unsupportedDocumentNotificationId, setUnsupportedDocumentNotificationId] = useState(0)
  const unsupportedDocumentTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (unsupportedDocumentTimer.current !== null) clearTimeout(unsupportedDocumentTimer.current)
  }, [])

  function dismissUnsupportedDocument() {
    setUnsupportedDocumentVisible(false)
    if (unsupportedDocumentTimer.current !== null) {
      clearTimeout(unsupportedDocumentTimer.current)
      unsupportedDocumentTimer.current = null
    }
  }

  function showUnsupportedDocument() {
    setUnsupportedDocumentVisible(true)
    setUnsupportedDocumentNotificationId((id) => id + 1)
    if (unsupportedDocumentTimer.current !== null) clearTimeout(unsupportedDocumentTimer.current)
    unsupportedDocumentTimer.current = setTimeout(dismissUnsupportedDocument, 5000)
  }

  return (
    <div className="flex h-full flex-col bg-base text-primary">
      <AdminHeader tab={tab} onTabChange={setTab} />
      <main className="flex-1 overflow-auto p-5">
        <div className="admin-tab-stack">
          <section
            data-testid="admin-tab-deliveries"
            data-active={tab === 'deliveries'}
            className="admin-tab-panel"
            aria-hidden={tab !== 'deliveries'}
            inert={tab !== 'deliveries'}
          >
            <DeliveriesTab onUnsupportedDocument={showUnsupportedDocument} selectedUserId={deliveryUserId} onFilterUserIdChange={(userId) => setDeliveryUserId(userId === '' ? undefined : userId)} />
          </section>
          <section
            data-testid="admin-tab-users"
            data-active={tab === 'users'}
            className="admin-tab-panel"
            aria-hidden={tab !== 'users'}
            inert={tab !== 'users'}
          >
            <UsersTab onViewDeliveries={(userId) => { setDeliveryUserId(userId); setTab('deliveries') }} />
          </section>
        </div>
      </main>
      <AdminErrorNotification
        key={unsupportedDocumentNotificationId}
        visible={unsupportedDocumentVisible}
        onDismiss={dismissUnsupportedDocument}
      />
    </div>
  )
}
