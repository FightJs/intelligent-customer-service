import { expect, it } from 'vitest'
import { demoRequest } from '../src/demo/backend'

it('把五轮采集的同一份需求带入订单、方案与演示后台', async () => {
  sessionStorage.clear()
  const request = (path: string, body?: object) =>
    demoRequest('/api' + path, body ? { method: 'POST', body: JSON.stringify(body) } : {})
  const { session_id } = await (await request('/session', {})).json()
  const answers = ['测试家居', '25㎡', '6 万', '一名主播坐播', '月底试播']
  for (const message of answers) {
    expect((await request('/chat', { session_id, message })).ok).toBe(true)
  }
  const survey = await (await request('/session/' + session_id)).json()
  expect(survey.form_complete).toBe(true)
  expect(survey.form_state.completed).toBe(false)
  expect(survey.form_state.sections.budget.fields.total.value).toBe('5-10w')

  expect((await request('/orders', { session_id })).ok).toBe(true)
  const { id } = await (await request('/pipeline', { session_id })).json()
  const plan = await (await request('/pipeline/' + id)).json()
  expect(plan.title).toContain('测试家居')
  expect(plan.budget).toBe('5-10 万')
  const { items } = await (await request('/admin/deliverables')).json()
  expect(items[0].markdown).toContain('月底试播')
  expect(items[0].session_id).toBe(session_id)
})
