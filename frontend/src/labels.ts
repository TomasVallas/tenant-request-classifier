import type { Category, HistoryStatus, Urgency } from './types.ts'

export const CATEGORY_LABELS: Record<Category, string> = {
  vika: 'Vika',
  laskutus: 'Laskutus',
  muutto: 'Muutto',
  muu: 'Muu',
}

export const URGENCY_LABELS: Record<Urgency, string> = {
  kiireellinen: 'Kiireellinen',
  normaali: 'Normaali',
}

export const STATUS_LABELS: Record<HistoryStatus, string> = {
  odottaa: 'Odottaa',
  hyvaksytty: 'Hyväksytty',
}

const RULE_LABELS: Record<string, string> = {
  low_confidence: 'Matala varmuus',
  category_muu: 'Luokka on muu',
  urgent_requires_review: 'Kiireellinen vaatii tarkistuksen',
}

const EMERGENCY_PREFIX = 'emergency_keyword:'

export function formatRuleHit(rule: string): string {
  if (rule.startsWith(EMERGENCY_PREFIX)) {
    return `Hätäsana: ${rule.slice(EMERGENCY_PREFIX.length)}`
  }
  return RULE_LABELS[rule] ?? rule
}
