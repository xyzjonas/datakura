// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest'
import { doubleEncodePath, fetchWithEncodedPath } from '../encode-api-path'

describe('doubleEncodePath', () => {
  it.each([
    ['/api/v1/products/AB%2F12', '/api/v1/products/AB%252F12'],
    ['/api/v1/products/A%20B', '/api/v1/products/A%2520B'],
    ['/api/v1/products/100%25', '/api/v1/products/100%2525'],
    ['/api/v1/products/PLAIN-1/audits', '/api/v1/products/PLAIN-1/audits'],
  ])('%s -> %s', (input, expected) => {
    expect(doubleEncodePath(new URL(`http://localhost${input}`)).pathname).toBe(expected)
  })

  it('keeps the query string', () => {
    const url = doubleEncodePath(new URL('http://localhost/api/v1/products/A%2FB?q=a%2Fb&x=1'))
    expect(url.search).toBe('?q=a%2Fb&x=1')
  })
})

describe('fetchWithEncodedPath', () => {
  afterEach(() => vi.unstubAllGlobals())

  function stubFetch() {
    const fetchMock = vi.fn<(request: Request) => Promise<Response>>(async () => new Response("{}"))
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  it('double encodes escaped API paths', async () => {
    const fetchMock = stubFetch()
    await fetchWithEncodedPath(new Request('http://localhost/api/v1/products/AB%2F12'))
    expect(new URL(fetchMock.mock.calls[0][0].url).pathname).toBe('/api/v1/products/AB%252F12')
  })

  it('keeps method, headers and body of a write request', async () => {
    const fetchMock = stubFetch()
    await fetchWithEncodedPath(
      new Request('http://localhost/api/v1/products/AB%2F12', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': 'abc' },
        body: JSON.stringify({ name: 'x' }),
      }),
    )
    const sent = fetchMock.mock.calls[0][0]
    expect(sent.method).toBe('PUT')
    expect(sent.headers.get('X-CSRFToken')).toBe('abc')
    expect(await sent.json()).toEqual({ name: 'x' })
  })

  it.each(['http://localhost/api/v1/products/PLAIN-1', 'http://localhost/static/a%20b.js'])(
    'leaves %s untouched',
    async (url) => {
      const fetchMock = stubFetch()
      await fetchWithEncodedPath(new Request(url))
      expect(fetchMock.mock.calls[0][0].url).toBe(url)
    },
  )
})
