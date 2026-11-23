import { useEffect, useRef, useState } from 'react'
import { CATEGORY_LABELS, URGENCY_LABELS, formatRuleHit } from '../labels.ts'
import type { ClassificationResult } from '../types.ts'

interface ResultCardProps {
  result: ClassificationResult
  isApproved: boolean
  onApprove: () => void
}

type CopyState = 'idle' | 'copied' | 'failed'

const COPY_FEEDBACK_MS = 2500

function AlertIcon() {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 3 2 21h20L12 3Zm0 6v6m0 3v.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function ResultCard({ result, isApproved, onApprove }: ResultCardProps) {
  const [reply, setReply] = useState(result.reply_draft)
  const [copyState, setCopyState] = useState<CopyState>('idle')
  const headingRef = useRef<HTMLHeadingElement>(null)

  const isUrgent = result.urgency === 'kiireellinen'
  const isLowConfidence = result.rule_hits.includes('low_confidence')
  const confidencePercent = Math.round(result.confidence * 100)

  // Moves keyboard and screen reader users to the new result, and scrolls to it on phones.
  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  useEffect(() => {
    if (copyState === 'idle') return
    const timer = window.setTimeout(() => setCopyState('idle'), COPY_FEEDBACK_MS)
    return () => window.clearTimeout(timer)
  }, [copyState])

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(reply)
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }
  }

  return (
    <article className="result">
      <h2 ref={headingRef} className="section-title" tabIndex={-1}>
        Tulos
      </h2>

      <dl className="result__facts">
        <div>
          <dt>Luokka</dt>
          <dd>
            <span className="badge">{CATEGORY_LABELS[result.category]}</span>
          </dd>
        </div>
        <div>
          <dt>Kiireellisyys</dt>
          <dd>
            <span className={isUrgent ? 'badge badge--urgent' : 'badge badge--calm'}>
              {isUrgent && <AlertIcon />}
              {URGENCY_LABELS[result.urgency]}
            </span>
          </dd>
        </div>
        <div className="result__confidence">
          <dt>Varmuus</dt>
          <dd>
            <span className="confidence__value">{confidencePercent} %</span>
            <span className="confidence__track" aria-hidden="true">
              <span
                className={
                  isLowConfidence
                    ? 'confidence__fill confidence__fill--low'
                    : 'confidence__fill'
                }
                style={{ width: `${confidencePercent}%` }}
              />
            </span>
          </dd>
        </div>
      </dl>

      {result.needs_human && (
        <p className="notice notice--warning">
          <AlertIcon />
          Tarkistettava ihmisen toimesta
        </p>
      )}

      {result.provider === 'fake' && (
        <p className="notice notice--info">
          Demotila: tulos perustuu avainsanoihin, ei kielimalliin.
        </p>
      )}

      <section className="result__section">
        <h3 className="result__subtitle">Tiivistelmä</h3>
        <p>{result.summary}</p>
      </section>

      {result.rule_hits.length > 0 && (
        <p className="rule-hits">
          Sääntöosumat: {result.rule_hits.map(formatRuleHit).join(', ')}
        </p>
      )}

      <div className="result__section">
        <label className="field-label" htmlFor="reply-draft">
          Vastausehdotus
        </label>
        <textarea
          id="reply-draft"
          className="textarea"
          rows={6}
          value={reply}
          readOnly={isApproved}
          onChange={(event) => setReply(event.target.value)}
        />
      </div>

      <div className="result__actions">
        <button type="button" className="button button--secondary" onClick={handleCopy}>
          {copyState === 'copied' ? 'Kopioitu' : 'Kopioi'}
        </button>
        <button
          type="button"
          className="button button--primary"
          disabled={isApproved || reply.trim().length === 0}
          onClick={onApprove}
        >
          {isApproved ? 'Hyväksytty' : 'Hyväksy'}
        </button>
        <span className="result__feedback" role="status">
          {copyState === 'copied' && 'Vastaus kopioitu leikepöydälle.'}
          {copyState === 'failed' && 'Kopiointi epäonnistui. Kopioi teksti käsin.'}
        </span>
      </div>

      <p className="result__footnote">Kielimalli ehdottaa – ihminen päättää</p>
    </article>
  )
}
