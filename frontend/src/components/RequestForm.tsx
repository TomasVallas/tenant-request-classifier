import { useState } from 'react'
import type { FormEvent } from 'react'
import { MAX_REQUEST_LENGTH } from '../types.ts'

interface RequestFormProps {
  value: string
  onChange: (value: string) => void
  onSubmit: (text: string) => void
  isLoading: boolean
  statusMessage?: string | null
}

const numberFormat = new Intl.NumberFormat('fi-FI')
const MAX_LABEL = numberFormat.format(MAX_REQUEST_LENGTH)

const EMPTY_ERROR = 'Kirjoita palvelupyyntö ennen lähettämistä.'
const TOO_LONG_ERROR = `Palvelupyyntö saa olla enintään ${MAX_LABEL} merkkiä.`

export function RequestForm({
  value,
  onChange,
  onSubmit,
  isLoading,
  statusMessage = null,
}: RequestFormProps) {
  const [triedEmptySubmit, setTriedEmptySubmit] = useState(false)

  const trimmed = value.trim()
  const isTooLong = trimmed.length > MAX_REQUEST_LENGTH
  const showEmptyError = triedEmptySubmit && trimmed.length === 0
  const error = isTooLong ? TOO_LONG_ERROR : showEmptyError ? EMPTY_ERROR : null

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isLoading || isTooLong) return
    if (trimmed.length === 0) {
      setTriedEmptySubmit(true)
      return
    }
    setTriedEmptySubmit(false)
    onSubmit(trimmed)
  }

  return (
    <form className="request-form" onSubmit={handleSubmit} noValidate>
      <label className="field-label" htmlFor="request-text">
        Vuokralaisen palvelupyyntö
      </label>
      <textarea
        id="request-text"
        className="textarea"
        rows={7}
        value={value}
        readOnly={isLoading}
        placeholder="Esimerkiksi: Keittiön hana vuotaa, asunto B12."
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? 'request-counter request-error' : 'request-counter'}
        onChange={(event) => {
          setTriedEmptySubmit(false)
          onChange(event.target.value)
        }}
      />
      <div className="request-form__meta">
        {error ? (
          <p id="request-error" className="field-error" role="alert">
            {error}
          </p>
        ) : (
          <span />
        )}
        <span
          id="request-counter"
          className={isTooLong ? 'counter counter--over' : 'counter'}
        >
          {numberFormat.format(trimmed.length)} / {MAX_LABEL}
        </span>
      </div>
      <div className="request-form__actions">
        <button type="submit" className="button button--primary" disabled={isLoading}>
          {isLoading ? 'Luokitellaan…' : 'Luokittele pyyntö'}
        </button>
        <span className="request-form__status" role="status">
          {statusMessage}
        </span>
      </div>
    </form>
  )
}
