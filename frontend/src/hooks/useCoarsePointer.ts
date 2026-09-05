import { useMediaQuery } from './useMediaQuery'

const COARSE_POINTER_QUERY = '(pointer: coarse)'

/**
 * 是否为触屏（粗指针）设备。桌面端返回 false。
 * jsdom 等无 matchMedia 的环境安全兜底为 false。
 */
export function useCoarsePointer(): boolean {
  return useMediaQuery(COARSE_POINTER_QUERY)
}
