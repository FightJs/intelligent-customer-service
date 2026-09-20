/**
 * 智能交付页面设计原型交互
 * 对齐 docs/compose/spec/plan-delivery-pages.md
 */

const CATEGORY_LABEL = {
  equipment: '设备参数',
  scheme: '搭建方案',
  vertical: '垂类知识',
}

const PLAN_STATUS = {
  ready: { label: '可下载', badge: 'badge--done' },
  running: { label: '生成中', badge: 'badge--run' },
  partial: { label: '部分完成', badge: 'badge--warn' },
  failed: { label: '失败', badge: 'badge--fail' },
  pending: { label: '排队中', badge: 'badge--idle' },
}

const SKILL_STATUS = {
  succeeded: { label: '已完成', dot: 'is-done' },
  running: { label: '生成中', dot: 'is-run' },
  partial: { label: '部分完成', dot: 'is-warn' },
  failed: { label: '失败', dot: 'is-fail' },
  pending: { label: '等待中', dot: '' },
}

/** Mock 数据 — 与后端 pipeline 契约对齐 */
const PLANS = [
  {
    id: 'pr_01',
    title: '跃步球鞋 · 25㎡ 实战篮球鞋直播间',
    industry: '鞋靴',
    roomSize: '25㎡ 中型',
    budget: '3–5 万',
    status: 'ready',
    updatedAt: '2026-09-10 14:22',
    skills: {
      plan: 'succeeded',
      images: 'succeeded',
      video: 'succeeded',
      package: 'succeeded',
    },
    images: [
      { angle: 'front', label: '正面 0°', name: '鞋墙主视角', visual: 'visual-front' },
      { angle: 'left', label: '左侧 120°', name: '布光与鞋墙', visual: 'visual-left' },
      { angle: 'rear', label: '背面 240°', name: '动线与纵深', visual: 'visual-rear' },
    ],
    video: { durationSec: 8, resolution: '720P' },
    pdf: {
      title: '跃步直播间搭建方案',
      sections: ['需求摘要', '空间布局', '设备清单', '三档套餐', '搭建步骤', '风险提示'],
    },
    packageFileCount: 6,
  },
  {
    id: 'pr_02',
    title: '美妆小间 · 10㎡ 补光优化',
    industry: '美妆',
    roomSize: '10㎡ 小型',
    budget: '1–2 万',
    status: 'running',
    updatedAt: '2026-09-10 15:01',
    progress: 72,
    skills: {
      plan: 'succeeded',
      images: 'running',
      video: 'pending',
      package: 'pending',
    },
    images: [
      { angle: 'front', label: '正面 0°', name: '已完成', visual: 'visual-front' },
      { angle: 'left', label: '左侧 120°', name: '生成中…', visual: 'visual-left' },
      { angle: 'rear', label: '背面 240°', name: '排队中', missing: true },
    ],
    video: null,
    pdf: {
      title: '美妆小间方案草稿',
      sections: ['需求摘要', '布光方案', '设备清单'],
    },
    packageFileCount: null,
  },
  {
    id: 'pr_03',
    title: '食品工厂直播 · 半成品方案',
    industry: '食品',
    roomSize: '40㎡ 大型',
    budget: '效果优先',
    status: 'partial',
    updatedAt: '2026-09-09 18:40',
    skills: {
      plan: 'succeeded',
      images: 'partial',
      video: 'failed',
      package: 'succeeded',
    },
    images: [
      { angle: 'front', label: '正面 0°', name: '主播主视角', visual: 'visual-front' },
      { angle: 'left', label: '左侧 120°', name: '缺失机位', missing: true },
      { angle: 'rear', label: '背面 240°', name: '线材收纳', visual: 'visual-rear' },
    ],
    video: { failed: true, message: '图生视频超时，可在后端管线重试该 skill' },
    pdf: {
      title: '食品工厂直播间方案',
      sections: ['需求摘要', '空间分区', '设备清单', '三档套餐', '搭建步骤'],
    },
    packageFileCount: 5,
  },
  {
    id: 'pr_04',
    title: '珠宝鉴赏间 · 生成失败样例',
    industry: '珠宝',
    roomSize: '15㎡ 小型',
    budget: '5 万+',
    status: 'failed',
    updatedAt: '2026-09-08 09:30',
    skills: {
      plan: 'succeeded',
      images: 'failed',
      video: 'pending',
      package: 'pending',
    },
    images: [
      { angle: 'front', label: '正面 0°', name: '生成失败', missing: true },
      { angle: 'left', label: '左侧 120°', name: '未开始', missing: true },
      { angle: 'rear', label: '背面 240°', name: '未开始', missing: true },
    ],
    video: null,
    pdf: {
      title: '珠宝鉴赏间方案',
      sections: ['需求摘要', '安全布光', '设备清单'],
    },
    packageFileCount: null,
  },
]

const KNOWLEDGE_DOCS = [
  {
    id: 'kb_1',
    filename: '鞋靴布光与鞋墙陈列手册.pdf',
    category: 'vertical',
    status: 'ready',
    chunks: 42,
    updatedAt: '2026-09-08 11:20',
    note: '含三点布光、色温、鞋墙层次；按小标题切块',
  },
  {
    id: 'kb_2',
    filename: '爱图仕灯光参数表-2026.pdf',
    category: 'equipment',
    status: 'ready',
    chunks: 68,
    updatedAt: '2026-09-07 09:15',
    note: '整行一块，结构化字段进 metadata',
  },
  {
    id: 'kb_3',
    filename: '跃步25㎡实战篮球鞋套餐方案.pdf',
    category: 'scheme',
    status: 'ready',
    chunks: 12,
    updatedAt: '2026-09-06 16:40',
    note: '含三档 package_tiers 与 equipment_ids',
  },
  {
    id: 'kb_4',
    filename: '食品直播间动线规范.pdf',
    category: 'vertical',
    status: 'embedding',
    chunks: 0,
    updatedAt: '2026-09-10 14:55',
    note: '切块完成，正在写入 Milvus',
  },
  {
    id: 'kb_5',
    filename: '声卡与收音设备清单.pdf',
    category: 'equipment',
    status: 'pending',
    chunks: 0,
    updatedAt: '2026-09-10 15:02',
    note: '等待队列',
  },
  {
    id: 'kb_6',
    filename: '珠宝直播间安全与布光.pdf',
    category: 'vertical',
    status: 'failed',
    chunks: 0,
    updatedAt: '2026-09-05 10:11',
    note: 'Embedding 服务超时，可重新向量化',
  },
]

let activePlanId = PLANS[0].id
let lightboxIndex = 0
let toastTimer = null

/* ── Routing ─────────────────────────────────────────────── */

function setRoute(route) {
  document.querySelectorAll('.page').forEach((el) => {
    el.classList.toggle('is-active', el.dataset.page === route)
  })
  document.querySelectorAll('[data-route]').forEach((btn) => {
    const on = btn.dataset.route === route
    if (btn.classList.contains('top-nav-btn')) {
      btn.setAttribute('aria-current', on ? 'page' : 'false')
    }
  })
}

document.querySelectorAll('[data-route]').forEach((btn) => {
  btn.addEventListener('click', () => setRoute(btn.dataset.route))
})

/* ── Toast ───────────────────────────────────────────────── */

function toast(message, kind = '') {
  const el = document.getElementById('toast')
  el.textContent = message
  el.className = `toast is-open ${kind ? `is-${kind}` : ''}`
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    el.classList.remove('is-open')
  }, 2800)
}

/* ── Plans ───────────────────────────────────────────────── */

function renderPlanList() {
  const root = document.getElementById('plans-list')
  const count = document.getElementById('plans-count')
  count.textContent = String(PLANS.length)

  root.innerHTML = PLANS.map((p) => {
    const st = PLAN_STATUS[p.status]
    const active = p.id === activePlanId
    return `
      <button type="button" class="plan-item ${active ? 'is-active' : ''}" data-plan-id="${p.id}">
        <span class="plan-item__title">${p.title}</span>
        <span class="plan-item__meta">
          <span>${p.industry} · ${p.roomSize}</span>
          <span class="badge ${st.badge}">${st.label}</span>
        </span>
        <span class="plan-item__meta" style="margin-top:2px; display:block; font-size:10px;">${p.updatedAt}</span>
      </button>
    `
  }).join('')

  root.querySelectorAll('[data-plan-id]').forEach((btn) => {
    btn.addEventListener('click', () => {
      activePlanId = btn.dataset.planId
      renderPlanList()
      renderPlanDetail()
    })
  })
}

function skillChip(label, key, skills) {
  const state = SKILL_STATUS[skills[key]]
  return `
    <div class="skill-chip">
      <span class="skill-chip__label">${label}</span>
      <span class="skill-chip__state"><i class="dot ${state.dot}"></i>${state.label}</span>
    </div>
  `
}

function renderPlanDetail() {
  const root = document.getElementById('plan-detail')
  const plan = PLANS.find((p) => p.id === activePlanId)
  if (!plan) {
    root.innerHTML = `
      <div class="empty-state">
        <strong>暂无方案</strong>
        <span>完成工作台调研并提交订单后，智能交付会生成预览图、视频与清单。</span>
      </div>`
    return
  }

  const st = PLAN_STATUS[plan.status]
  const statusExtra =
    plan.status === 'running'
      ? ` · 进度 ${plan.progress ?? 0}% · 可离开，完成后可回来查看`
      : plan.status === 'partial'
        ? ' · 部分产物失败，方案 PDF 仍可下载'
        : plan.status === 'failed'
          ? ' · 管线失败 · 可按 skill 单独重试'
          : ''

  const gallery = plan.images
    .map((img, i) => {
      if (img.missing) {
        return `
          <button type="button" class="gallery-card" data-img-index="${i}" disabled>
            <div class="gallery-card__visual visual-missing">该机位暂未生成</div>
            <div class="gallery-card__overlay">
              <span class="gallery-card__angle">${img.label}</span>
              <span class="gallery-card__name">${img.name}</span>
            </div>
          </button>`
      }
      return `
        <button type="button" class="gallery-card" data-img-index="${i}" aria-label="放大查看 ${img.label}">
          <div class="gallery-card__visual ${img.visual}"></div>
          <div class="gallery-card__overlay">
            <span class="gallery-card__angle">${img.label}</span>
            <span class="gallery-card__name">${img.name}</span>
          </div>
        </button>`
    })
    .join('')

  let videoHtml = ''
  if (plan.video?.failed) {
    videoHtml = `
      <div class="video-error">
        ${plan.video.message}
        <div style="margin-top:12px">
          <button type="button" class="btn btn--danger btn--sm" data-retry-skill="preview_video">重试预览视频</button>
        </div>
      </div>`
  } else if (plan.video) {
    videoHtml = `
      <div class="video-shell">
        <div class="video-stage">
          <button type="button" class="video-stage__play" aria-label="播放预览视频">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          </button>
        </div>
        <div class="video-meta">
          <span>${plan.video.durationSec}s · ${plan.video.resolution} · 无声漫游预览</span>
          <span>基于正面机位 i2v</span>
        </div>
      </div>`
  } else {
    videoHtml = `
      <div class="empty-state" style="border:1px solid rgb(var(--color-outline)); border-radius:10px; background:rgb(var(--color-recess));">
        <strong>视频生成中</strong>
        <span>预览图就绪后将自动提交图生视频任务（约 1–4 分钟）</span>
      </div>`
  }

  const packageBar =
    plan.packageFileCount != null
      ? `
      <div class="package-bar">
        <div>
          <strong>完整交付包</strong>
          <span>${plan.packageFileCount} 个文件 · 图 / 视频 / 方案 PDF / 说明</span>
        </div>
        <button type="button" class="btn btn--primary" id="btn-download-package">下载完整交付包</button>
      </div>`
      : `
      <div class="package-bar">
        <div>
          <strong>完整交付包</strong>
          <span>全部 skill 完成后可打包下载</span>
        </div>
        <button type="button" class="btn btn--primary" disabled>下载完整交付包</button>
      </div>`

  root.innerHTML = `
    <div class="plan-detail__header">
      <div>
        <h2>${plan.title}</h2>
        <p>${plan.industry} · ${plan.roomSize} · 预算 ${plan.budget} · 更新于 ${plan.updatedAt}</p>
      </div>
      <span class="badge ${st.badge}">${st.label}${statusExtra ? '' : ''}</span>
    </div>
    ${statusExtra ? `<p style="margin:-6px 0 12px; font-size:12px; color:rgb(var(--color-muted));">${statusExtra.trim()}</p>` : ''}

    <div class="skill-strip" aria-label="管线进度">
      ${skillChip('方案 PDF', 'plan', plan.skills)}
      ${skillChip('预览图', 'images', plan.skills)}
      ${skillChip('预览视频', 'video', plan.skills)}
      ${skillChip('交付包', 'package', plan.skills)}
    </div>

    <section class="section">
      <div class="section__head">
        <h3>360° 预览图</h3>
        <span>${
          plan.skills.images === 'failed'
            ? '<button type="button" class="btn btn--ghost btn--sm" data-retry-skill="preview_images">重试图集</button>'
            : '三机位连贯静帧 · 0° / 120° / 240°'
        }</span>
      </div>
      <div class="gallery">${gallery}</div>
    </section>

    <section class="section">
      <div class="section__head">
        <h3>预览视频</h3>
        <span>${plan.video && !plan.video.failed ? '5–15s 环绕 / 漫游' : ''}</span>
      </div>
      ${videoHtml}
    </section>

    <section class="section">
      <div class="section__head">
        <h3>方案清单 PDF</h3>
        <span>设备购买 · 套餐方案 · 搭建规划</span>
      </div>
      <div class="pdf-card">
        <div class="pdf-icon">PDF</div>
        <div>
          <h4>${plan.pdf.title}</h4>
          <p>含设备清单、三档套餐与可执行搭建步骤</p>
          <div class="pdf-sections">
            ${plan.pdf.sections.map((s) => `<span>${s}</span>`).join('')}
          </div>
        </div>
        <button type="button" class="btn btn--ghost" id="btn-download-pdf">下载 PDF</button>
      </div>
    </section>

    ${packageBar}
  `

  root.querySelectorAll('[data-img-index]:not([disabled])').forEach((btn) => {
    btn.addEventListener('click', () => openLightbox(Number(btn.dataset.imgIndex)))
  })
  root.querySelector('#btn-download-pdf')?.addEventListener('click', () => {
    toast('原型：将触发鉴权下载 plan.pdf', 'done')
  })
  root.querySelector('#btn-download-package')?.addEventListener('click', () => {
    toast('原型：将下载完整交付包 zip', 'done')
  })
  root.querySelector('.video-stage__play')?.addEventListener('click', () => {
    toast('原型：播放预览视频', 'done')
  })
  root.querySelectorAll('[data-retry-skill]').forEach((btn) => {
    btn.addEventListener('click', () => {
      toast(`原型：已提交「${btn.dataset.retrySkill}」重试`, 'done')
    })
  })
}

document.getElementById('btn-refresh-plans').addEventListener('click', () => {
  toast('已刷新管线状态', 'done')
})

/* ── Lightbox ────────────────────────────────────────────── */

function openLightbox(index) {
  const plan = PLANS.find((p) => p.id === activePlanId)
  if (!plan) return
  lightboxIndex = index
  updateLightbox()
  document.getElementById('lightbox').classList.add('is-open')
}

function updateLightbox() {
  const plan = PLANS.find((p) => p.id === activePlanId)
  if (!plan) return
  const img = plan.images[lightboxIndex]
  const stage = document.getElementById('lightbox-stage')
  stage.className = `lightbox__stage ${img.visual}`
  document.getElementById('lightbox-title').textContent = img.label
  document.getElementById('lightbox-sub').textContent = img.name
}

function closeLightbox() {
  document.getElementById('lightbox').classList.remove('is-open')
}

document.getElementById('lightbox-close').addEventListener('click', closeLightbox)
document.getElementById('lightbox').addEventListener('click', (e) => {
  if (e.target.id === 'lightbox') closeLightbox()
})
document.getElementById('lightbox-prev').addEventListener('click', () => {
  const plan = PLANS.find((p) => p.id === activePlanId)
  lightboxIndex = (lightboxIndex - 1 + plan.images.length) % plan.images.length
  updateLightbox()
})
document.getElementById('lightbox-next').addEventListener('click', () => {
  const plan = PLANS.find((p) => p.id === activePlanId)
  lightboxIndex = (lightboxIndex + 1) % plan.images.length
  updateLightbox()
})

document.addEventListener('keydown', (e) => {
  const lb = document.getElementById('lightbox')
  if (!lb.classList.contains('is-open')) return
  if (e.key === 'Escape') closeLightbox()
  if (e.key === 'ArrowLeft') document.getElementById('lightbox-prev').click()
  if (e.key === 'ArrowRight') document.getElementById('lightbox-next').click()
})

/* ── Knowledge base ──────────────────────────────────────── */

const KB_STATUS = {
  ready: { label: '就绪', badge: 'badge--done' },
  embedding: { label: '向量化中', badge: 'badge--warn' },
  pending: { label: '待处理', badge: 'badge--idle' },
  failed: { label: '失败', badge: 'badge--fail' },
}

function filteredDocs() {
  const q = document.getElementById('kb-search').value.trim().toLowerCase()
  const status = document.getElementById('kb-status').value
  const category = document.getElementById('kb-category').value
  return KNOWLEDGE_DOCS.filter((d) => {
    if (q && !d.filename.toLowerCase().includes(q)) return false
    if (status && d.status !== status) return false
    if (category && d.category !== category) return false
    return true
  })
}

function renderStats() {
  const total = KNOWLEDGE_DOCS.length
  const ready = KNOWLEDGE_DOCS.filter((d) => d.status === 'ready').length
  const embedding = KNOWLEDGE_DOCS.filter((d) => d.status === 'embedding').length
  const failed = KNOWLEDGE_DOCS.filter((d) => d.status === 'failed').length
  document.getElementById('knowledge-stats').innerHTML = [
    ['文档总数', total],
    ['就绪', ready],
    ['向量化中', embedding],
    ['失败', failed],
  ]
    .map(
      ([label, value]) => `
      <div class="stat-card">
        <div>
          <div class="stat-card__label">${label}</div>
          <div class="stat-card__value">${value}</div>
        </div>
      </div>`
    )
    .join('')
}

function renderKnowledgeTable() {
  const tbody = document.getElementById('kb-tbody')
  const docs = filteredDocs()
  if (!docs.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6">
          <div class="empty-state">
            <strong>没有匹配的文档</strong>
            <span>调整筛选条件，或上传新的 PDF 入向量库</span>
          </div>
        </td>
      </tr>`
    return
  }

  tbody.innerHTML = docs
    .map((d) => {
      const st = KB_STATUS[d.status]
      return `
        <tr data-doc-id="${d.id}">
          <td>${d.filename}</td>
          <td>${CATEGORY_LABEL[d.category]}</td>
          <td><span class="badge ${st.badge}">${st.label}</span></td>
          <td>${d.chunks || '—'}</td>
          <td style="color:rgb(var(--color-muted))">${d.updatedAt}</td>
          <td>
            <div class="row-actions">
              <button type="button" class="btn btn--ghost btn--sm" data-action="detail">详情</button>
              ${
                d.status === 'failed'
                  ? `<button type="button" class="btn btn--ghost btn--sm" data-action="reembed">重试</button>`
                  : ''
              }
              <button type="button" class="btn btn--danger btn--sm" data-action="delete">删除</button>
            </div>
          </td>
        </tr>`
    })
    .join('')

  tbody.querySelectorAll('tr[data-doc-id]').forEach((tr) => {
    tr.querySelectorAll('[data-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const doc = KNOWLEDGE_DOCS.find((d) => d.id === tr.dataset.docId)
        const action = btn.dataset.action
        if (action === 'detail') openDrawer(doc)
        if (action === 'reembed') {
          doc.status = 'embedding'
          doc.updatedAt = nowLabel()
          toast('已重新提交向量化', 'done')
          refreshKnowledge()
        }
        if (action === 'delete') {
          if (!confirm(`删除「${doc.filename}」？将从向量库移除全部 chunk。`)) return
          const i = KNOWLEDGE_DOCS.findIndex((d) => d.id === doc.id)
          KNOWLEDGE_DOCS.splice(i, 1)
          toast('文档已删除', 'done')
          refreshKnowledge()
        }
      })
    })
  })
}

function refreshKnowledge() {
  renderStats()
  renderKnowledgeTable()
}

function nowLabel() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function openDrawer(doc) {
  const backdrop = document.getElementById('drawer-backdrop')
  const drawer = document.getElementById('drawer')
  const st = KB_STATUS[doc.status]
  drawer.hidden = false
  drawer.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
      <div>
        <h3>${doc.filename}</h3>
        <div class="meta">${CATEGORY_LABEL[doc.category]} · ${doc.updatedAt}</div>
      </div>
      <button type="button" class="btn btn--ghost btn--sm" id="drawer-close">关闭</button>
    </div>
    <div style="margin-bottom:12px;"><span class="badge ${st.badge}">${st.label}</span></div>
    <dl>
      <dt>分类</dt><dd>${CATEGORY_LABEL[doc.category]}</dd>
      <dt>Chunks</dt><dd>${doc.chunks || '—'}</dd>
      <dt>Collection</dt><dd>${
        doc.category === 'equipment'
          ? 'equipment_specs'
          : doc.category === 'scheme'
            ? 'setup_schemes'
            : 'vertical_knowledge'
      }</dd>
      <dt>说明</dt><dd>${doc.note || '—'}</dd>
    </dl>
    <p style="font-size:12px; color:rgb(var(--color-muted)); margin:0 0 16px;">
      切块后写入 dense + BM25 sparse；检索时按 industry / room_size / budget 过滤。
    </p>
    <div class="drawer-actions">
      <button type="button" class="btn btn--ghost btn--sm" id="drawer-reembed">重新向量化</button>
      <button type="button" class="btn btn--danger btn--sm" id="drawer-delete">删除文档</button>
    </div>
  `
  backdrop.classList.add('is-open')
  document.getElementById('drawer-close').addEventListener('click', closeDrawer)
  document.getElementById('drawer-reembed').addEventListener('click', () => {
    doc.status = 'embedding'
    doc.updatedAt = nowLabel()
    closeDrawer()
    toast('已重新提交向量化', 'done')
    refreshKnowledge()
  })
  document.getElementById('drawer-delete').addEventListener('click', () => {
    if (!confirm(`删除「${doc.filename}」？`)) return
    const i = KNOWLEDGE_DOCS.findIndex((d) => d.id === doc.id)
    KNOWLEDGE_DOCS.splice(i, 1)
    closeDrawer()
    toast('文档已删除', 'done')
    refreshKnowledge()
  })
}

function closeDrawer() {
  document.getElementById('drawer-backdrop').classList.remove('is-open')
  document.getElementById('drawer').hidden = true
}

document.getElementById('drawer-backdrop').addEventListener('click', closeDrawer)

document.getElementById('kb-search').addEventListener('input', renderKnowledgeTable)
document.getElementById('kb-status').addEventListener('change', renderKnowledgeTable)
document.getElementById('kb-category').addEventListener('change', renderKnowledgeTable)

/* Upload */

const uploadZone = document.getElementById('upload-zone')
const pdfInput = document.getElementById('pdf-input')

document.getElementById('btn-pick-pdf').addEventListener('click', () => pdfInput.click())

pdfInput.addEventListener('change', () => {
  const file = pdfInput.files?.[0]
  if (file) ingestPdf(file.name)
  pdfInput.value = ''
})

;['dragenter', 'dragover'].forEach((ev) => {
  uploadZone.addEventListener(ev, (e) => {
    e.preventDefault()
    uploadZone.classList.add('is-dragover')
  })
})
;['dragleave', 'drop'].forEach((ev) => {
  uploadZone.addEventListener(ev, (e) => {
    e.preventDefault()
    uploadZone.classList.remove('is-dragover')
  })
})
uploadZone.addEventListener('drop', (e) => {
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    toast('仅支持 PDF 文件', 'fail')
    return
  }
  ingestPdf(file.name)
})

function ingestPdf(filename) {
  const category = document.getElementById('upload-category').value
  KNOWLEDGE_DOCS.unshift({
    id: `kb_${Date.now()}`,
    filename,
    category,
    status: 'pending',
    chunks: 0,
    updatedAt: nowLabel(),
    note: '已上传，等待切块与向量化',
  })
  refreshKnowledge()
  toast(`「${filename}」已加入向量化队列`, 'done')

  // 模拟：pending → embedding → ready
  setTimeout(() => {
    const doc = KNOWLEDGE_DOCS.find((d) => d.filename === filename)
    if (!doc || doc.status !== 'pending') return
    doc.status = 'embedding'
    doc.updatedAt = nowLabel()
    refreshKnowledge()
  }, 900)
  setTimeout(() => {
    const doc = KNOWLEDGE_DOCS.find((d) => d.filename === filename)
    if (!doc || doc.status !== 'embedding') return
    doc.status = 'ready'
    doc.chunks = 8 + Math.floor(Math.random() * 40)
    doc.updatedAt = nowLabel()
    refreshKnowledge()
    toast(`「${filename}」已就绪 · ${doc.chunks} chunks`, 'done')
  }, 2600)
}

/* ── Init ────────────────────────────────────────────────── */

renderPlanList()
renderPlanDetail()
refreshKnowledge()
