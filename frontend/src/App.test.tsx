import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.tsx'
import { ApiError, classify, wakeBackend } from './api.ts'
import { makeResult } from './test/fixtures.ts'
import type { ClassificationResult } from './types.ts'
import { WAKING_NOTICE_DELAY_MS } from './useBackendWakeUp.ts'

vi.mock('./api.ts', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./api.ts')>()),
  classify: vi.fn(),
  wakeBackend: vi.fn(),
}))

const classifyMock = vi.mocked(classify)
const wakeMock = vi.mocked(wakeBackend)
const STORAGE_KEY = 'tenant-request-classifier.history.v1'
const WAKING_TEXT = /Ensimmäinen haku voi kestää noin 30 sekuntia/

async function submitExample(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Vika' }))
  await user.click(screen.getByRole('button', { name: 'Luokittele pyyntö' }))
}

beforeEach(() => {
  classifyMock.mockReset()
  wakeMock.mockReset()
  wakeMock.mockResolvedValue(true)
})

describe('App backend wake-up', () => {
  function pendingWake() {
    let finish: (ok: boolean) => void = () => {}
    wakeMock.mockReturnValue(
      new Promise((resolve) => {
        finish = resolve
      }),
    )
    return (ok: boolean) => finish(ok)
  }

  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('wakes the backend when the page opens', async () => {
    render(<App />)
    await act(async () => {})
    expect(wakeMock).toHaveBeenCalledOnce()
    expect(classifyMock).not.toHaveBeenCalled()
  })

  it('shows a notice while the backend starts and hides it when ready', async () => {
    const finish = pendingWake()
    render(<App />)
    expect(screen.queryByText(WAKING_TEXT)).not.toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(WAKING_NOTICE_DELAY_MS)
    })
    expect(screen.getByText(WAKING_TEXT)).toBeInTheDocument()

    await act(async () => {
      finish(true)
    })
    expect(screen.queryByText(WAKING_TEXT)).not.toBeInTheDocument()
  })

  it('shows no notice when the backend is already running', async () => {
    render(<App />)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(WAKING_NOTICE_DELAY_MS * 2)
    })
    expect(screen.queryByText(WAKING_TEXT)).not.toBeInTheDocument()
  })

  it('explains the wait once when classifying during startup', async () => {
    const finishWake = pendingWake()
    let finishClassify: (result: ClassificationResult) => void = () => {}
    classifyMock.mockReturnValue(
      new Promise((resolve) => {
        finishClassify = resolve
      }),
    )
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Vika' }))
    fireEvent.click(screen.getByRole('button', { name: 'Luokittele pyyntö' }))
    act(() => {
      vi.advanceTimersByTime(WAKING_NOTICE_DELAY_MS)
    })

    expect(screen.getAllByText(WAKING_TEXT)).toHaveLength(1)
    expect(screen.queryByText('Luokitellaan pyyntöä…')).not.toBeInTheDocument()

    await act(async () => {
      finishWake(true)
      finishClassify(makeResult())
    })
    expect(screen.queryByText(WAKING_TEXT)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Vastausehdotus')).toBeInTheDocument()
  })
})

describe('App', () => {
  it('shows the empty states first', () => {
    render(<App />)
    expect(screen.getByText(/niin tulos näkyy tässä/)).toBeInTheDocument()
    expect(screen.getByText('Ei vielä käsiteltyjä pyyntöjä.')).toBeInTheDocument()
  })

  it('does not call the API for an empty request', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Luokittele pyyntö' }))

    expect(classifyMock).not.toHaveBeenCalled()
  })

  it('classifies a request and adds it to history', async () => {
    const user = userEvent.setup()
    classifyMock.mockResolvedValue(makeResult())
    render(<App />)

    await submitExample(user)

    expect(classifyMock).toHaveBeenCalledWith('Keittiön hana vuotaa, asunto B12.')
    expect(await screen.findByLabelText('Vastausehdotus')).toBeInTheDocument()
    const history = screen.getByRole('region', { name: 'Historia' })
    expect(within(history).getByText('Odottaa')).toBeInTheDocument()
  })

  it('shows a loading state and blocks a second submission', async () => {
    const user = userEvent.setup()
    let finish: (result: ClassificationResult) => void = () => {}
    classifyMock.mockReturnValue(
      new Promise((resolve) => {
        finish = resolve
      }),
    )
    render(<App />)

    await submitExample(user)

    expect(screen.getByText('Luokitellaan pyyntöä…')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Luokitellaan…' })).toBeDisabled()

    finish(makeResult())
    expect(await screen.findByLabelText('Vastausehdotus')).toBeInTheDocument()
    expect(classifyMock).toHaveBeenCalledOnce()
  })

  it('shows a clear error from the API', async () => {
    const user = userEvent.setup()
    classifyMock.mockRejectedValue(new ApiError('Kielimalli ei ole käytettävissä.', 503))
    render(<App />)

    await submitExample(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Kielimalli ei ole käytettävissä.')
    expect(screen.getByText('Ei vielä käsiteltyjä pyyntöjä.')).toBeInTheDocument()
  })

  it('scrolls an error into view', async () => {
    const user = userEvent.setup()
    const scrollIntoView = vi.spyOn(Element.prototype, 'scrollIntoView')
    classifyMock.mockRejectedValue(new ApiError('Palvelin ei vastaa.'))
    render(<App />)

    await submitExample(user)
    await screen.findByRole('alert')

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'nearest' })
    scrollIntoView.mockRestore()
  })

  it('marks an approved request in history without sending anything', async () => {
    const user = userEvent.setup()
    classifyMock.mockResolvedValue(makeResult())
    render(<App />)
    await submitExample(user)

    await user.click(await screen.findByRole('button', { name: 'Hyväksy' }))

    const history = screen.getByRole('region', { name: 'Historia' })
    expect(within(history).getByText('Hyväksytty')).toBeInTheDocument()
    expect(classifyMock).toHaveBeenCalledOnce()
  })

  it('stores history without the request text', async () => {
    const user = userEvent.setup()
    classifyMock.mockResolvedValue(makeResult())
    render(<App />)

    await submitExample(user)
    await screen.findByLabelText('Vastausehdotus')

    const stored = localStorage.getItem(STORAGE_KEY) ?? ''
    expect(JSON.parse(stored)).toHaveLength(1)
    expect(stored).not.toContain('hana')
    expect(stored).not.toContain('Kiitos')
  })

  it('restores history after a reload', async () => {
    const user = userEvent.setup()
    classifyMock.mockResolvedValue(makeResult())
    const { unmount } = render(<App />)
    await submitExample(user)
    await screen.findByLabelText('Vastausehdotus')
    unmount()

    render(<App />)

    const history = screen.getByRole('region', { name: 'Historia' })
    expect(within(history).getByText('Odottaa')).toBeInTheDocument()
  })

  it('clears history', async () => {
    const user = userEvent.setup()
    classifyMock.mockResolvedValue(makeResult())
    render(<App />)
    await submitExample(user)
    await screen.findByLabelText('Vastausehdotus')

    await user.click(screen.getByRole('button', { name: 'Tyhjennä' }))

    expect(screen.getByText('Ei vielä käsiteltyjä pyyntöjä.')).toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')).toEqual([])
  })

  it('can still approve a result after history was cleared', async () => {
    const user = userEvent.setup()
    classifyMock.mockResolvedValue(makeResult())
    render(<App />)
    await submitExample(user)
    await screen.findByLabelText('Vastausehdotus')
    await user.click(screen.getByRole('button', { name: 'Tyhjennä' }))

    await user.click(screen.getByRole('button', { name: 'Hyväksy' }))

    const history = screen.getByRole('region', { name: 'Historia' })
    expect(within(history).getByText('Hyväksytty')).toBeInTheDocument()
  })
})
