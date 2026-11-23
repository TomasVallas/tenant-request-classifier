import { useEffect, useRef, useState } from 'react'
import { ApiError, classify } from './api.ts'
import { ExampleButtons } from './components/ExampleButtons.tsx'
import { HistoryList } from './components/HistoryList.tsx'
import { RequestForm } from './components/RequestForm.tsx'
import { ResultCard } from './components/ResultCard.tsx'
import { createHistoryItem, loadHistory, saveHistory, upsertHistoryItem } from './history.ts'
import type { ClassificationResult, HistoryItem } from './types.ts'

interface CurrentResult {
  result: ClassificationResult
  item: HistoryItem
}

const GENERIC_ERROR = 'Luokittelu epäonnistui. Yritä hetken kuluttua uudelleen.'

export default function App() {
  const [text, setText] = useState('')
  const [current, setCurrent] = useState<CurrentResult | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const errorRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    saveHistory(history)
  }, [history])

  // On phones the result area is below the form, so make sure the error is seen.
  useEffect(() => {
    if (error) errorRef.current?.scrollIntoView({ block: 'nearest' })
  }, [error])

  async function handleSubmit(requestText: string) {
    setIsLoading(true)
    setError(null)
    setCurrent(null)
    try {
      const result = await classify(requestText)
      const item = createHistoryItem(result)
      setCurrent({ result, item })
      setHistory((previous) => upsertHistoryItem(previous, item))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : GENERIC_ERROR)
    } finally {
      setIsLoading(false)
    }
  }

  function handleApprove() {
    if (!current) return
    const approved: HistoryItem = { ...current.item, status: 'hyvaksytty' }
    setCurrent({ ...current, item: approved })
    setHistory((previous) => upsertHistoryItem(previous, approved))
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1 className="app__title">Palvelupyyntöjen luokittelija</h1>
        <p className="app__lead">
          Kielimalli ehdottaa, säännöt ja ihminen päättävät. Mitään ei lähetetä automaattisesti.
        </p>
      </header>

      <main className="layout">
        <section className="panel layout__form" aria-labelledby="request-title">
          <h2 id="request-title" className="section-title">
            Uusi pyyntö
          </h2>
          <ExampleButtons onSelect={setText} disabled={isLoading} />
          <RequestForm
            value={text}
            onChange={setText}
            onSubmit={handleSubmit}
            isLoading={isLoading}
          />
        </section>

        <section className="panel layout__result" aria-label="Luokittelun tulos" aria-busy={isLoading}>
          {isLoading && (
            <div className="state" role="status">
              <span className="spinner" aria-hidden="true" />
              Luokitellaan pyyntöä…
            </div>
          )}
          {!isLoading && error && (
            <>
              <h2 className="section-title">Tulos</h2>
              <p ref={errorRef} className="notice notice--error" role="alert">
                {error}
              </p>
            </>
          )}
          {!isLoading && !error && !current && (
            <>
              <h2 className="section-title">Tulos</h2>
              <p className="empty-text">
                Kirjoita palvelupyyntö tai valitse esimerkki, niin tulos näkyy tässä.
              </p>
            </>
          )}
          {!isLoading && current && (
            <ResultCard
              key={current.item.id}
              result={current.result}
              isApproved={current.item.status === 'hyvaksytty'}
              onApprove={handleApprove}
            />
          )}
        </section>

        <div className="layout__history">
          <HistoryList items={history} onClear={() => setHistory([])} />
        </div>
      </main>

      <footer className="app__footer">
        Portfoliodemo kuvitteelliselle vuokrataloyhtiölle. Älä syötä oikeita henkilötietoja.
      </footer>
    </div>
  )
}
