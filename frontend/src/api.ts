import { CATEGORIES, URGENCIES } from './types.ts'
import type { ClassificationResult } from './types.ts'

// Long enough for a backend that is waking up from zero replicas.
const REQUEST_TIMEOUT_MS = 45_000
const WAKE_TIMEOUT_MS = 60_000

const CONNECTION_ERROR = 'Palvelimeen ei saada yhteyttä. Yritä hetken kuluttua uudelleen.'
const TIMEOUT_ERROR = 'Palvelin ei vastannut ajoissa. Yritä hetken kuluttua uudelleen.'
const UNEXPECTED_ERROR = 'Palvelin palautti odottamattoman vastauksen. Yritä uudelleen.'

const configuredUrl =
  import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')
const API_URL = configuredUrl.replace(/\/+$/, '')

export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

// TypeScript types disappear at runtime, so data from the network is checked here.
function isClassificationResult(value: unknown): value is ClassificationResult {
  if (!isRecord(value)) return false
  return (
    CATEGORIES.some((category) => category === value.category) &&
    URGENCIES.some((urgency) => urgency === value.urgency) &&
    typeof value.summary === 'string' &&
    typeof value.reply_draft === 'string' &&
    typeof value.confidence === 'number' &&
    typeof value.needs_human === 'boolean' &&
    Array.isArray(value.rule_hits) &&
    value.rule_hits.every((rule) => typeof rule === 'string') &&
    typeof value.provider === 'string' &&
    typeof value.latency_ms === 'number'
  )
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (isRecord(body) && typeof body.detail === 'string') return body.detail
  } catch {
    // The error body was not JSON, so the general message below is used.
  }
  return UNEXPECTED_ERROR
}

// Starts a sleeping backend before the first request. It makes no model call, so it is free.
export async function wakeBackend(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/api/health`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(WAKE_TIMEOUT_MS),
    })
    return response.ok
  } catch {
    return false
  }
}

export async function classify(text: string): Promise<ClassificationResult> {
  let response: Response
  try {
    response = await fetch(`${API_URL}/api/classify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    })
  } catch (error) {
    const timedOut = error instanceof DOMException && error.name === 'TimeoutError'
    throw new ApiError(timedOut ? TIMEOUT_ERROR : CONNECTION_ERROR)
  }

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status)
  }

  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new ApiError(UNEXPECTED_ERROR, response.status)
  }

  if (!isClassificationResult(body)) {
    throw new ApiError(UNEXPECTED_ERROR, response.status)
  }
  return body
}
