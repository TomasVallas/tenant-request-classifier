import { CATEGORIES, HISTORY_STATUSES, URGENCIES } from './types.ts'
import type { ClassificationResult, HistoryItem } from './types.ts'

const STORAGE_KEY = 'tenant-request-classifier.history.v1'
export const MAX_HISTORY_ITEMS = 50

function isHistoryItem(value: unknown): value is HistoryItem {
  if (typeof value !== 'object' || value === null) return false
  const item = value as Record<string, unknown>
  return (
    typeof item.id === 'string' &&
    typeof item.createdAt === 'string' &&
    !Number.isNaN(Date.parse(item.createdAt)) &&
    CATEGORIES.some((category) => category === item.category) &&
    URGENCIES.some((urgency) => urgency === item.urgency) &&
    HISTORY_STATUSES.some((status) => status === item.status)
  )
}

// localStorage can throw when it is blocked or full, and stored data can be corrupted.
export function loadHistory(): HistoryItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return []
    const parsed: unknown = JSON.parse(stored)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isHistoryItem).slice(0, MAX_HISTORY_ITEMS)
  } catch {
    return []
  }
}

export function saveHistory(items: HistoryItem[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch {
    // The app keeps working for this session without saved history.
  }
}

export function createHistoryItem(result: ClassificationResult): HistoryItem {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    createdAt: new Date().toISOString(),
    category: result.category,
    urgency: result.urgency,
    status: 'odottaa',
  }
}

export function upsertHistoryItem(items: HistoryItem[], item: HistoryItem): HistoryItem[] {
  const exists = items.some((existing) => existing.id === item.id)
  const updated = exists
    ? items.map((existing) => (existing.id === item.id ? item : existing))
    : [item, ...items]
  return updated.slice(0, MAX_HISTORY_ITEMS)
}
