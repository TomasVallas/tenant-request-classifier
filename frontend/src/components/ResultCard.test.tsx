import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { makeResult } from '../test/fixtures.ts'
import { ResultCard } from './ResultCard.tsx'

const HUMAN_NOTICE = 'Tarkistettava ihmisen toimesta'

describe('ResultCard', () => {
  it('shows category, urgency, confidence and summary', () => {
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)

    expect(screen.getByText('Vika')).toBeInTheDocument()
    expect(screen.getByText('Normaali')).toBeInTheDocument()
    expect(screen.getByText('87 %')).toBeInTheDocument()
    expect(screen.getByText('Keittiön hana vuotaa asunnossa B12.')).toBeInTheDocument()
    expect(screen.getByText('Kielimalli ehdottaa – ihminen päättää')).toBeInTheDocument()
  })

  it('makes an urgent request stand out', () => {
    render(
      <ResultCard
        result={makeResult({ urgency: 'kiireellinen' })}
        isApproved={false}
        onApprove={vi.fn()}
      />,
    )
    expect(screen.getByText('Kiireellinen')).toHaveClass('badge--urgent')
  })

  it('shows the human review notice when needed', () => {
    render(
      <ResultCard result={makeResult({ needs_human: true })} isApproved={false} onApprove={vi.fn()} />,
    )
    expect(screen.getByText(HUMAN_NOTICE)).toBeInTheDocument()
  })

  it('hides the human review notice when not needed', () => {
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)
    expect(screen.queryByText(HUMAN_NOTICE)).not.toBeInTheDocument()
  })

  it('shows rule hits in readable form', () => {
    const result = makeResult({
      rule_hits: ['emergency_keyword:vesivuoto', 'urgent_requires_review'],
    })
    render(<ResultCard result={result} isApproved={false} onApprove={vi.fn()} />)

    expect(
      screen.getByText('Sääntöosumat: Hätäsana: vesivuoto, Kiireellinen vaatii tarkistuksen'),
    ).toBeInTheDocument()
  })

  it('marks fake provider results clearly', () => {
    render(
      <ResultCard result={makeResult({ provider: 'fake' })} isApproved={false} onApprove={vi.fn()} />,
    )
    expect(screen.getByText(/Demotila/)).toBeInTheDocument()
  })

  it('does not show the demo notice for a real model', () => {
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)
    expect(screen.queryByText(/Demotila/)).not.toBeInTheDocument()
  })

  it('moves focus to the new result', () => {
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)
    expect(screen.getByRole('heading', { name: 'Tulos' })).toHaveFocus()
  })

  it('scrolls a result that appears low on the screen into view', () => {
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView
    const rect = vi
      .spyOn(Element.prototype, 'getBoundingClientRect')
      .mockReturnValue({ top: window.innerHeight } as DOMRect)

    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start' })
    rect.mockRestore()
  })

  it('does not scroll a result that is already visible', () => {
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView

    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)

    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  it('lets the user edit and copy the reply', async () => {
    const user = userEvent.setup()
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)
    const reply = screen.getByLabelText('Vastausehdotus')

    await user.clear(reply)
    await user.type(reply, 'Muokattu vastaus')
    await user.click(screen.getByRole('button', { name: 'Kopioi' }))

    await expect(navigator.clipboard.readText()).resolves.toBe('Muokattu vastaus')
    expect(screen.getByRole('status')).toHaveTextContent('Vastaus kopioitu')
  })

  it('tells the user when copying fails', async () => {
    const user = userEvent.setup()
    vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValueOnce(new Error('blocked'))
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: 'Kopioi' }))

    expect(screen.getByRole('status')).toHaveTextContent('Kopiointi epäonnistui')
  })

  it('calls onApprove from the approve button', async () => {
    const user = userEvent.setup()
    const onApprove = vi.fn()
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={onApprove} />)

    await user.click(screen.getByRole('button', { name: 'Hyväksy' }))

    expect(onApprove).toHaveBeenCalledOnce()
  })

  it('does not allow approving an empty reply', async () => {
    const user = userEvent.setup()
    render(<ResultCard result={makeResult()} isApproved={false} onApprove={vi.fn()} />)

    await user.clear(screen.getByLabelText('Vastausehdotus'))

    expect(screen.getByRole('button', { name: 'Hyväksy' })).toBeDisabled()
  })

  it('locks an approved reply', () => {
    render(<ResultCard result={makeResult()} isApproved onApprove={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Hyväksytty' })).toBeDisabled()
    expect(screen.getByLabelText('Vastausehdotus')).toHaveAttribute('readonly')
  })
})
