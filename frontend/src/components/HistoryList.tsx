import { CATEGORY_LABELS, STATUS_LABELS, URGENCY_LABELS } from '../labels.ts'
import type { HistoryItem } from '../types.ts'

interface HistoryListProps {
  items: HistoryItem[]
  onClear: () => void
}

const dateFormat = new Intl.DateTimeFormat('fi-FI', {
  dateStyle: 'short',
  timeStyle: 'short',
})

export function HistoryList({ items, onClear }: HistoryListProps) {
  return (
    <section className="panel history" aria-labelledby="history-title">
      <div className="history__header">
        <h2 id="history-title" className="section-title">
          Historia
        </h2>
        {items.length > 0 && (
          <button type="button" className="button button--ghost" onClick={onClear}>
            Tyhjennä
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <p className="empty-text">Ei vielä käsiteltyjä pyyntöjä.</p>
      ) : (
        <ul className="history__list">
          {items.map((item) => (
            <li key={item.id} className="history__item">
              <time className="history__time" dateTime={item.createdAt}>
                {dateFormat.format(new Date(item.createdAt))}
              </time>
              <span className="badge">{CATEGORY_LABELS[item.category]}</span>
              <span
                className={
                  item.urgency === 'kiireellinen' ? 'badge badge--urgent' : 'badge badge--calm'
                }
              >
                {URGENCY_LABELS[item.urgency]}
              </span>
              <span
                className={
                  item.status === 'hyvaksytty'
                    ? 'history__status history__status--approved'
                    : 'history__status'
                }
              >
                {STATUS_LABELS[item.status]}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
