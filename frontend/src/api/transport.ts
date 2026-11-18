export const isPagesDemo = import.meta.env.MODE === 'pages-demo'

export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  if (isPagesDemo) {
    const { demoRequest } = await import('../demo/backend')
    return demoRequest(url, init)
  }
  return fetch(url, init)
}
