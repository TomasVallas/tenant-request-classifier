import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { MAX_REQUEST_LENGTH } from '../types.ts'
import { RequestForm } from './RequestForm.tsx'

function renderForm(initialValue = '', isLoading = false) {
  const onSubmit = vi.fn()

  function Wrapper() {
    const [value, setValue] = useState(initialValue)
    return (
      <RequestForm value={value} onChange={setValue} onSubmit={onSubmit} isLoading={isLoading} />
    )
  }

  render(<Wrapper />)
  return { onSubmit, user: userEvent.setup() }
}

const submitButton = () => screen.getByRole('button', { name: 'Luokittele pyyntö' })

describe('RequestForm', () => {
  it.each(['', '   \n  '])('blocks an empty submission', async (value) => {
    const { onSubmit, user } = renderForm(value)

    await user.click(submitButton())

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('Kirjoita palvelupyyntö')
    expect(screen.getByLabelText('Vuokralaisen palvelupyyntö')).toBeInvalid()
  })

  it('removes the empty error when the user starts typing', async () => {
    const { user } = renderForm()
    await user.click(submitButton())

    await user.type(screen.getByLabelText('Vuokralaisen palvelupyyntö'), 'H')

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('submits trimmed text', async () => {
    const { onSubmit, user } = renderForm('  Hana vuotaa  ')

    await user.click(submitButton())

    expect(onSubmit).toHaveBeenCalledExactlyOnceWith('Hana vuotaa')
  })

  it('accepts text at the maximum length', async () => {
    const { onSubmit, user } = renderForm('a'.repeat(MAX_REQUEST_LENGTH))

    await user.click(submitButton())

    expect(onSubmit).toHaveBeenCalledOnce()
  })

  it('blocks text over the maximum length', async () => {
    const { onSubmit, user } = renderForm('a'.repeat(MAX_REQUEST_LENGTH + 1))

    await user.click(submitButton())

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('enintään')
  })

  it('shows the character count', () => {
    renderForm('Hana')
    expect(screen.getByText(/^4 \/ 2\s000$/)).toBeInTheDocument()
  })

  it('disables the button while loading', () => {
    renderForm('Hana vuotaa', true)
    expect(screen.getByRole('button', { name: 'Luokitellaan…' })).toBeDisabled()
  })
})
