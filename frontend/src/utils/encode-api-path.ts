const API_PREFIX = '/api/v1/'

/**
 * Django decodes `%2F` to `/` before URL routing, so codes containing a slash (e.g. `AB/12`)
 * would never match an API route. The path of every API request is therefore encoded twice
 * and the backend (`DoubleEncodedApiPathMiddleware`) decodes it once more before routing.
 */
export function doubleEncodePath(url: URL): URL {
  const encoded = new URL(url)
  encoded.pathname = url.pathname.replace(/%/g, '%25')
  return encoded
}

/** `fetch` replacement for the generated SDK client, see `doubleEncodePath` */
export async function fetchWithEncodedPath(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const request = new Request(input, init)
  const url = new URL(request.url)
  if (!url.pathname.startsWith(API_PREFIX) || !url.pathname.includes('%')) {
    return fetch(request)
  }

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD'
  return fetch(
    new Request(doubleEncodePath(url), {
      method: request.method,
      headers: request.headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      credentials: request.credentials,
      signal: request.signal,
      redirect: request.redirect,
    }),
  )
}
