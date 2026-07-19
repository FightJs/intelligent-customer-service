import '@testing-library/jest-dom'
import { beforeEach } from 'vitest'

// 每个 test 开始前清理 localStorage，避免跨用例状态泄漏
beforeEach(() => {
  localStorage.clear()
})
