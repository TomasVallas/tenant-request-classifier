import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ExampleButtons } from './ExampleButtons.tsx'

describe('ExampleButtons', () => {
  it('shows one example for each main case', () => {
    render(<ExampleButtons onSelect={vi.fn()} disabled={false} />)
    for (const name of ['Vika', 'Laskutus', 'Muutto', 'Kiireellinen']) {
      expect(screen.getByRole('button', { name })).toBeInTheDocument()
    }
  })

  it('passes the example text to the parent', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(<ExampleButtons onSelect={onSelect} disabled={false} />)

    await user.click(screen.getByRole('button', { name: 'Vika' }))

    expect(onSelect).toHaveBeenCalledWith('Keittiön hana vuotaa, asunto B12.')
  })

  it('disables the examples while loading', () => {
    render(<ExampleButtons onSelect={vi.fn()} disabled />)
    expect(screen.getByRole('button', { name: 'Vika' })).toBeDisabled()
  })
})
