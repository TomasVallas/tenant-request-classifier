import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { makeHistoryItem } from '../test/fixtures.ts'
import { HistoryList } from './HistoryList.tsx'

describe('HistoryList', () => {
  it('shows an empty state without a clear button', () => {
    render(<HistoryList items={[]} onClear={vi.fn()} />)

    expect(screen.getByText('Ei vielä käsiteltyjä pyyntöjä.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tyhjennä' })).not.toBeInTheDocument()
  })

  it('shows category, urgency and status for each item', () => {
    const items = [
      makeHistoryItem({ id: 'a', category: 'vika', urgency: 'kiireellinen' }),
      makeHistoryItem({ id: 'b', category: 'laskutus', status: 'hyvaksytty' }),
    ]
    render(<HistoryList items={items} onClear={vi.fn()} />)

    const [first, second] = screen.getAllByRole('listitem')
    expect(within(first).getByText('Vika')).toBeInTheDocument()
    expect(within(first).getByText('Kiireellinen')).toBeInTheDocument()
    expect(within(first).getByText('Odottaa')).toBeInTheDocument()
    expect(within(second).getByText('Laskutus')).toBeInTheDocument()
    expect(within(second).getByText('Hyväksytty')).toBeInTheDocument()
  })

  it('calls onClear from the clear button', async () => {
    const user = userEvent.setup()
    const onClear = vi.fn()
    render(<HistoryList items={[makeHistoryItem()]} onClear={onClear} />)

    await user.click(screen.getByRole('button', { name: 'Tyhjennä' }))

    expect(onClear).toHaveBeenCalledOnce()
  })
})
