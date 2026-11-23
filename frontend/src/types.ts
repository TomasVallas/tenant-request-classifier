// These types and limits mirror backend/app/schemas.py.
export const MAX_REQUEST_LENGTH = 2000

export const CATEGORIES = ['vika', 'laskutus', 'muutto', 'muu'] as const
export const URGENCIES = ['kiireellinen', 'normaali'] as const
export const HISTORY_STATUSES = ['odottaa', 'hyvaksytty'] as const

export type Category = (typeof CATEGORIES)[number]
export type Urgency = (typeof URGENCIES)[number]
export type HistoryStatus = (typeof HISTORY_STATUSES)[number]

export interface ClassificationResult {
  category: Category
  urgency: Urgency
  summary: string
  reply_draft: string
  confidence: number
  needs_human: boolean
  rule_hits: string[]
  provider: string
  latency_ms: number
}

// History stores no request text, so browser storage holds no tenant details.
export interface HistoryItem {
  id: string
  createdAt: string
  category: Category
  urgency: Urgency
  status: HistoryStatus
}
