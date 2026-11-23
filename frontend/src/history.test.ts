import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  MAX_HISTORY_ITEMS,
  createHistoryItem,
  loadHistory,
  saveHistory,
  upsertHistoryItem,
} from './history.ts'
import { makeHistoryItem, makeResult } from './test/fixtures.ts'

const STORAGE_KEY = 'tenant-request-classifier.history.v1'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('history storage', () => {
  it('saves and loads items', () => {
    const items = [makeHistoryItem()]
    saveHistory(items)
    expect(loadHistory()).toEqual(items)
  })

  it('returns an empty list when nothing is stored', () => {
    expect(loadHistory()).toEqual([])
  })

  it('survives corrupted JSON', () => {
    localStorage.setItem(STORAGE_KEY, '{not json')
    expect(loadHistory()).toEqual([])
  })

  it('drops items with an invalid shape', () => {
    const valid = makeHistoryItem()
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([valid, { id: 'x', category: 'keksitty' }, 'text', null]),
    )
    expect(loadHistory()).toEqual([valid])
  })

  it('survives blocked storage when loading', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(loadHistory()).toEqual([])
  })

  it('survives blocked storage when saving', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota')
    })
    expect(() => saveHistory([makeHistoryItem()])).not.toThrow()
  })
})

describe('history items', () => {
  it('stores no request text, summary or reply', () => {
    const result = makeResult({ summary: 'SALAINEN', reply_draft: 'SALAINEN' })
    const item = createHistoryItem(result)

    expect(JSON.stringify(item)).not.toContain('SALAINEN')
    expect(item.status).toBe('odottaa')
    expect(item.category).toBe(result.category)
  })

  it('adds a new item first', () => {
    const old = makeHistoryItem({ id: 'old' })
    const added = makeHistoryItem({ id: 'new' })
    expect(upsertHistoryItem([old], added)).toEqual([added, old])
  })

  it('updates an existing item in place', () => {
    const first = makeHistoryItem({ id: 'a' })
    const second = makeHistoryItem({ id: 'b' })
    const approved = { ...second, status: 'hyvaksytty' as const }
    expect(upsertHistoryItem([first, second], approved)).toEqual([first, approved])
  })

  it('keeps the list within the maximum size', () => {
    const items = Array.from({ length: MAX_HISTORY_ITEMS }, (_, index) =>
      makeHistoryItem({ id: String(index) }),
    )
    const updated = upsertHistoryItem(items, makeHistoryItem({ id: 'new' }))

    expect(updated).toHaveLength(MAX_HISTORY_ITEMS)
    expect(updated[0].id).toBe('new')
  })
})
