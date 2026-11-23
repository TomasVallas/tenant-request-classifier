import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { wakeBackend } from './api.ts'
import { WAKING_NOTICE_DELAY_MS, useBackendWakeUp } from './useBackendWakeUp.ts'

vi.mock('./api.ts', () => ({ wakeBackend: vi.fn() }))

const wakeMock = vi.mocked(wakeBackend)

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
  wakeMock.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useBackendWakeUp', () => {
  it('calls the backend once when mounted', () => {
    pendingWake()
    renderHook(() => useBackendWakeUp())
    expect(wakeMock).toHaveBeenCalledOnce()
  })

  it('does not report waking when the backend answers quickly', async () => {
    wakeMock.mockResolvedValue(true)
    const { result } = renderHook(() => useBackendWakeUp())

    await act(async () => {
      await vi.advanceTimersByTimeAsync(WAKING_NOTICE_DELAY_MS * 2)
    })

    expect(result.current).toBe(false)
  })

  it('reports waking after the delay until the backend answers', async () => {
    const finish = pendingWake()
    const { result } = renderHook(() => useBackendWakeUp())

    act(() => {
      vi.advanceTimersByTime(WAKING_NOTICE_DELAY_MS - 1)
    })
    expect(result.current).toBe(false)

    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(result.current).toBe(true)

    await act(async () => {
      finish(true)
    })
    expect(result.current).toBe(false)
  })

  it('stops reporting waking when the backend cannot be reached', async () => {
    const finish = pendingWake()
    const { result } = renderHook(() => useBackendWakeUp())
    act(() => {
      vi.advanceTimersByTime(WAKING_NOTICE_DELAY_MS)
    })

    await act(async () => {
      finish(false)
    })

    expect(result.current).toBe(false)
  })

  it('clears the timer when unmounted', () => {
    pendingWake()
    const { unmount } = renderHook(() => useBackendWakeUp())

    unmount()

    expect(vi.getTimerCount()).toBe(0)
  })
})
