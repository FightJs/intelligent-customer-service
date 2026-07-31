import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'

interface ZState {
  // id → 当前 z；卡片挂载时由 register 写入其 defaultZ，保证 Provider 感知所有卡片层级
  zs: Record<string, number>
  // 当前最大 z；0 表示尚未有人主动 bringToFront（此态下所有卡片都算 topmost）
  topZ: number
  bringToFront: (id: string) => void
  register: (id: string, defaultZ: number) => void
}

const ZStackContext = createContext<ZState | null>(null)

export function ZStackProvider({ children }: { children: ReactNode }) {
  const [zs, setZs] = useState<Record<string, number>>({})
  const [topZ, setTopZ] = useState(0)

  // 置顶：next = max(topZ, 所有已注册 z) + 1，确保置顶后严格大于现存任意卡片 z（含未置顶卡片的 defaultZ）。
  const bringToFront = useCallback((id: string) => {
    setZs((prevZs) => {
      const maxOfZs = Object.values(prevZs).reduce((m, v) => (v > m ? v : m), 0)
      const next = Math.max(topZ, maxOfZs) + 1
      setTopZ(next)
      return { ...prevZs, [id]: next }
    })
  }, [topZ])

  const register = useCallback((id: string, defaultZ: number) => {
    setZs((prev) => (prev[id] === undefined ? { ...prev, [id]: defaultZ } : prev))
  }, [])

  return (
    <ZStackContext.Provider value={{ zs, topZ, bringToFront, register }}>
      {children}
    </ZStackContext.Provider>
  )
}

export function useZStack(opts: { id: string; defaultZ?: number }): {
  z: number
  bringToFront: () => void
  isTopmost: boolean
} {
  const { id, defaultZ = 10 } = opts
  const ctx = useContext(ZStackContext)
  // 挂载时把自己的 defaultZ 注册进 Provider，使 bringToFront 计算最大值时能覆盖所有卡片
  useEffect(() => {
    if (ctx) ctx.register(id, defaultZ)
  }, [ctx, id, defaultZ])
  // 容错：不在 Provider 内时回退 defaultZ，并视作 topmost（孤立卡片自然在最顶）
  if (!ctx) return { z: defaultZ, bringToFront: () => {}, isTopmost: true }
  const z = ctx.zs[id] ?? defaultZ
  // 没人主动置顶（topZ=0）时所有卡片都算 topmost；否则只有 z===topMax 的那张是最顶。
  const isTopmost = ctx.topZ > 0 ? z === ctx.topZ : true
  return {
    z,
    bringToFront: () => ctx.bringToFront(id),
    isTopmost,
  }
}
