import { useCallback, useSyncExternalStore } from 'react'

export const MOBILE_LAYOUT_QUERY = (
  '(max-width: 640px), (max-width: 900px) and (max-height: 500px)'
)

function canMatchMedia(): boolean {
  return (
    typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
  )
}

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback((onChange: () => void) => {
    if (!canMatchMedia()) return () => {}

    const media = window.matchMedia(query)
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [query])

  const getSnapshot = useCallback(() => (
    canMatchMedia() && window.matchMedia(query).matches
  ), [query])

  return useSyncExternalStore(subscribe, getSnapshot, () => false)
}
