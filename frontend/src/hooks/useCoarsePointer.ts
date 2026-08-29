import { useSyncExternalStore } from 'react'

const COARSE_POINTER_QUERY = '(pointer: coarse)'

function canMatchMedia(): boolean {
  return (
    typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
  )
}

function subscribe(onChange: () => void): () => void {
  if (!canMatchMedia()) {
    return () => {}
  }

  const media = window.matchMedia(COARSE_POINTER_QUERY)
  media.addEventListener('change', onChange)
  return () => {
    media.removeEventListener('change', onChange)
  }
}

function getSnapshot(): boolean {
  if (!canMatchMedia()) {
    return false
  }
  return window.matchMedia(COARSE_POINTER_QUERY).matches
}

/**
 * 是否为触屏（粗指针）设备。桌面端返回 false。
 * jsdom 等无 matchMedia 的环境安全兜底为 false。
 */
export function useCoarsePointer(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => false)
}
