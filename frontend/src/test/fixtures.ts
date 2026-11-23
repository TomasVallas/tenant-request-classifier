import type { ClassificationResult, HistoryItem } from '../types.ts'

export function makeResult(overrides: Partial<ClassificationResult> = {}): ClassificationResult {
  return {
    category: 'vika',
    urgency: 'normaali',
    summary: 'Keittiön hana vuotaa asunnossa B12.',
    reply_draft: 'Kiitos ilmoituksestasi. Kerrothan, milloin vika alkoi.',
    confidence: 0.87,
    needs_human: false,
    rule_hits: [],
    provider: 'openai',
    latency_ms: 120,
    ...overrides,
  }
}

export function makeHistoryItem(overrides: Partial<HistoryItem> = {}): HistoryItem {
  return {
    id: 'item-1',
    createdAt: '2026-11-23T10:15:00.000Z',
    category: 'vika',
    urgency: 'normaali',
    status: 'odottaa',
    ...overrides,
  }
}
