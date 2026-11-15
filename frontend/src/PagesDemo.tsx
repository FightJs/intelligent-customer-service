import WorkbenchPreview from './screens/WorkbenchPreview'

export default function PagesDemo() {
  return <>
    <div role="status" style={{ padding: '12px 20px', background: '#fff2c7', color: '#3e320e', lineHeight: 1.5 }}>
      前端演示：全部内容均为示例数据。登录、数据保存、AI 调用及订单服务未接入；选择和加入操作仅在当前页面模拟。
    </div>
    <WorkbenchPreview demo />
  </>
}
