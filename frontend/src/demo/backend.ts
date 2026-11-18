import JSZip from 'jszip'
import type { AdminDeliveryDetail, AdminUser, SessionData, ChatResult } from '../api/client'
import type { PlanDetailRaw } from '../api/pipeline'
import { surveyLines, wordDocument } from './documents'
import { applyDemoAnswer, demoForm, demoSteps } from './survey'

type DemoSession = SessionData & { turn: number; submitted: boolean }
type DemoState = { sessions: DemoSession[]; deliveries: AdminDeliveryDetail[]; plans: PlanDetailRaw[] }
const stateKey = 'ics_demo_backend_v1'
const date = '2026-08-16'
const demoUser = { id: 1, username: '演示访客', role: 'admin' } as const
const users: AdminUser[] = [{ ...demoUser, created_at: date }, { id: 2, username: '示例运营', role: 'user', created_at: date }]
const json = (data: unknown, status = 200) => Response.json(data, { status })
const missing = () => json({ detail: '没有找到该演示记录' }, 404)
const samples = ['front.png', 'left.png', 'rear.png', 'preview.mp4', 'plan.pdf']

function readState(): DemoState {
  return JSON.parse(sessionStorage.getItem(stateKey) ?? '{"sessions":[],"deliveries":[],"plans":[]}')
}

function saveState(state: DemoState) {
  sessionStorage.setItem(stateKey, JSON.stringify(state))
}

function label(session: DemoSession, section: 'customer' | 'venue' | 'budget', field: string) {
  return String(session.form_state.sections[section].fields[field]?.value || '')
}

function planFor(session: DemoSession): PlanDetailRaw {
  const roomSize = label(session, 'venue', 'area')
  const budget = label(session, 'budget', 'total').replace(/w/, ' 万')
  return {
    id: 'demo-' + session.session_id, session_id: session.session_id,
    title: (label(session, 'customer', 'brand') || '青屿家居') + ' · 模拟直播间方案',
    industry: '家居', roomSize: roomSize ? roomSize + '㎡' : '面积待确认', budget,
    status: 'ready', updated_at: date,
    skills: { plan: 'succeeded', images: 'succeeded', video: 'succeeded', package: 'succeeded' },
    images: ['front', 'left', 'rear'].map((angle, i) => ({
      angle, label: ['正面 0°', '左侧 120°', '背面 240°'][i],
      name: ['主机位布置示意', '侧面布光示意', '后方动线示意'][i], url: '/demo-media/' + angle + '.png',
      width: 960, height: 540,
    })),
    video: { durationSec: 6, resolution: '960×540', url: '/demo-media/preview.mp4' },
    pdf: { title: '直播间搭建示例方案', sections: ['布局', '设备', '实施步骤'], url: '/demo-media/plan.pdf' },
    packageFileCount: samples.length + 2,
    plan: {
      meta: { brand: label(session, 'customer', 'brand'), industry: '家居', room_size: roomSize, budget_total: budget },
      summary: '模拟方案，以一名主播和桌面商品展示为示例。附带的图、视频及 PDF 为固定样张。',
      layout: {
        zones: [{ name: '主播区', notes: '桌面用于演示收纳用品，背景预留品牌陈列面。' }, { name: '机位与布光区', notes: '主机位正对桌面，侧灯避开镜面反光。' }, { name: '动线', notes: '预留后方取货通道，线缆沿墙布置。' }],
        lighting_plan: '柔光主灯从斜前方布置，侧后方辅灯勾勒轮廓。',
        camera_plan: '主机位拍半身，补充俯拍产品特写。',
        background_plan: '暖灰背景配浅木色陈列架。',
      },
      equipment_list: [
        { category: '相机', name: '主机位相机', qty: 1, model: '示例 4K 相机', reason: '直播主画面' },
        { category: '灯光', name: '柔光灯', qty: 2, reason: '主光与轮廓光分离' },
        { category: '音频', name: '无线领夹麦', qty: 1, reason: '便于主播移动展示' },
      ],
      package_tiers: [
        { tier: '基础', total_range: '¥8,000–15,000', items: [{ name: '相机与领夹麦' }] },
        { tier: '标准', total_range: '¥15,000–30,000', items: [{ name: '双灯与桌面展示套件' }] },
        { tier: '进阶', total_range: '¥30,000–50,000', items: [{ name: '双机位与辅助监看' }] },
      ],
      setup_steps: ['丈量现场并规划线路', '定位主机、主光与收音', '陈列商品并测试直播画面'],
      risks: ['玻璃产品反光需现场调整', '安装前确认供电与网络'],
    },
  }
}

function page<T>(items: T[], params: URLSearchParams) {
  const size = Number(params.get('size')) || 10
  const page = Number(params.get('page')) || 1
  return { items: items.slice((page - 1) * size, page * size), total: items.length, page, size }
}

const asset = (name: string) => fetch(import.meta.env.BASE_URL + 'demo-media/' + name)

export async function demoRequest(url: string, init: RequestInit = {}): Promise<Response> {
  init.signal?.throwIfAborted()
  const { pathname, searchParams } = new URL(url, location.origin)
  const path = pathname.replace(/^\/api/, '')
  const method = init.method ?? 'GET'
  const body = init.body ? JSON.parse(String(init.body)) : {}
  const state = readState()
  const sessionById = (id: string | null) => state.sessions.find(session => session.session_id === id)

  if (path === '/auth/guest' || path === '/auth/login' || path === '/auth/register') return json({ token: 'pages-demo', user: demoUser })
  if (path === '/auth/me') return json(demoUser)
  if (path === '/session' && method === 'POST') {
    const session: DemoSession = {
      session_id: crypto.randomUUID(), greeting: '欢迎体验直播间搭建工作台。下面用五轮示例对话走完需求采集。\n\n' + demoSteps[0].question,
      form_state: demoForm(0), form_complete: false, messages: [], turn: 0, submitted: false,
    }
    state.sessions.push(session)
    saveState(state)
    return json(session)
  }
  if (path === '/session/latest') return state.sessions.length ? json(state.sessions.at(-1)) : missing()

  const sessionId = path.startsWith('/session/') ? path.split('/')[2] : body.session_id ?? searchParams.get('session_id')
  const session = sessionById(sessionId)
  if (path.startsWith('/session/') && method === 'GET') return session ? json(session) : missing()
  if (path === '/chat' || path === '/chat/stream' || path.endsWith('/skip')) {
    if (!session) return missing()
    const skipped = path.endsWith('/skip')
    if (session.turn < demoSteps.length) {
      applyDemoAnswer(session.form_state, session.turn, skipped || body.message === '使用示例回答' ? demoSteps[session.turn].sample : String(body.message ?? '').trim().slice(0, 200))
      session.turn += 1
    }
    const next = demoSteps[session.turn]
    const imageNote = body.images?.length ? '已在本页收到示例附件，本演示不分析图片。\n\n' : ''
    const reply = imageNote + (next
      ? `已${skipped ? '用示例数据补齐' : '记录并更新'}这部分需求。\n\n${next.question}`
      : '五轮演示采集已完成。你可以预览需求表，再点击「发送订单」，通过三步确认生成你的模拟交付方案。')
    const result: ChatResult = {
      reply, form_state: session.form_state, form_complete: !next, suggestions: [], tool_events: [],
    }
    session.form_complete = result.form_complete
    session.messages?.push({ role: 'user', content: skipped ? '使用示例数据' : String(body.message ?? '').slice(0, 200) }, { role: 'assistant', content: reply })
    saveState(state)
    if (path === '/chat/stream') {
      const event = (name: string, data: unknown) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`
      return new Response(
        event('start', { request_id: body.request_id, status: 'started' })
        + event('delta', { text: reply })
        + event('done', { ...result, request_id: body.request_id, assistant_message_id: session.turn }),
        { headers: { 'Content-Type': 'text/event-stream' } },
      )
    }
    return json(result)
  }
  if (path === '/generate/word') return session ? new Response(await wordDocument(session.form_state)) : missing()
  if (path === '/orders' && session) {
    let delivery = state.deliveries.find(item => item.session_id === sessionId)
    if (!delivery) {
      delivery = {
        id: state.deliveries.length + 1, session_id: sessionId, user_id: demoUser.id,
        customer_name: label(session, 'customer', 'brand') || '示例客户',
        created_at: date, owner_username: demoUser.username,
        submission_kind: body.allow_incomplete ? 'early' : 'complete',
        markdown: surveyLines(session.form_state).join('\n\n'),
      }
      state.deliveries.unshift(delivery)
    }
    session.submitted = true
    session.form_state.completed = true
    session.form_state.currentFieldId = ''
    session.form_complete = true
    saveState(state)
    return json({ delivery_id: delivery.id, sent: true, message: '模拟订单已提交' })
  }
  if (path === '/pipeline' && method === 'POST' && session) {
    const plan = planFor(session)
    state.plans = [plan, ...state.plans.filter(item => item.id !== plan.id)]
    saveState(state)
    return json({ id: plan.id, status: plan.status, message: '示例方案已准备好' })
  }
  if (path === '/pipeline') return json({ items: state.plans.map(p => ({ ...p, updatedAt: p.updated_at })) })
  if (path.startsWith('/pipeline/')) {
    const [id, action] = path.slice('/pipeline/'.length).split('/')
    const plan = state.plans.find(item => item.id === id)
    if (!plan) return missing()
    if (!action) return json(plan)
    if (action === 'package') {
      const zip = new JSZip()
      await Promise.all(samples.map(async name => {
        const response = await asset(name)
        if (!response.ok) throw new Error('无法加载示例交付文件')
        zip.file(name, await response.arrayBuffer())
      }))
      const linked = sessionById(plan.session_id ?? null)
      if (linked) zip.file('模拟需求确认书.docx', await (await wordDocument(linked.form_state)).arrayBuffer())
      zip.file('说明.txt', '图、视频和 PDF 为固定合成样张。需求确认书来自本次浏览器模拟采集。')
      return new Response(await zip.generateAsync({ type: 'blob', mimeType: 'application/zip' }))
    }
  }
  if (path.startsWith('/demo-media/') && samples.includes(path.split('/').at(-1)!)) return asset(path.split('/').at(-1)!)

  const matches = (value: string) => value.toLowerCase().includes((searchParams.get('search') ?? '').toLowerCase())
  if (path.startsWith('/admin/')) {
    if (method !== 'GET') return json({ detail: '公开演示的管理后台仅供查看，修改、删除和密码操作不可用。' }, 403)
    if (path === '/admin/users') return json({ ...page(users.filter(u => matches(u.username)), searchParams), admin_count: 1 })
    if (path.startsWith('/admin/users/')) {
      const user = users.find(item => item.id === Number(path.split('/').at(-1)))
      return user ? json({ ...user, delivery_count: state.deliveries.filter(item => item.user_id === user.id).length }) : missing()
    }
    if (path === '/admin/deliverables') return json(page(state.deliveries.filter(item =>
      matches(item.customer_name ?? '') && (!searchParams.get('user_id') || String(item.user_id) === searchParams.get('user_id'))), searchParams))
    if (path.startsWith('/admin/deliverables/')) {
      const delivery = state.deliveries.find(item => item.id === Number(path.split('/').at(-1)))
      return delivery ? json(delivery) : missing()
    }
  }
  return missing()
}
