import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, classify } from './api.ts'
import { makeResult } from './test/fixtures.ts'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function mockFetch(implementation: () => Promise<Response>) {
  const fetchMock = vi.fn(implementation)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('classify', () => {
  it('posts the text and returns the result', async () => {
    const result = makeResult()
    const fetchMock = mockFetch(async () => jsonResponse(result))

    await expect(classify('Hana vuotaa')).resolves.toEqual(result)

    const [url, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/api\/classify$/)
    expect(options.method).toBe('POST')
    expect(options.body).toBe(JSON.stringify({ text: 'Hana vuotaa' }))
  })

  it('shows the error message from the backend', async () => {
    mockFetch(async () => jsonResponse({ detail: 'Kielimalli ei ole käytettävissä.' }, 503))

    const error = await classify('Hana').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).message).toBe('Kielimalli ei ole käytettävissä.')
    expect((error as ApiError).status).toBe(503)
  })

  it('handles an error response that is not JSON', async () => {
    mockFetch(async () => new Response('Bad gateway', { status: 502 }))
    await expect(classify('Hana')).rejects.toThrow('odottamattoman vastauksen')
  })

  it('handles a network failure', async () => {
    mockFetch(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(classify('Hana')).rejects.toThrow('Palvelimeen ei saada yhteyttä')
  })

  it('handles a timeout', async () => {
    mockFetch(async () => {
      throw new DOMException('Timed out', 'TimeoutError')
    })
    await expect(classify('Hana')).rejects.toThrow('ei vastannut ajoissa')
  })

  it('rejects a response with the wrong shape', async () => {
    mockFetch(async () => jsonResponse({ ...makeResult(), category: 'keksitty' }))
    await expect(classify('Hana')).rejects.toThrow('odottamattoman vastauksen')
  })
})
