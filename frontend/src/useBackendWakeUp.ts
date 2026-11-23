import { useEffect, useState } from 'react'
import { wakeBackend } from './api.ts'

// A running backend answers faster than this, so the notice does not flash for nothing.
export const WAKING_NOTICE_DELAY_MS = 1500

/** Wakes the backend when the page opens and tells whether it is still starting. */
export function useBackendWakeUp(): boolean {
  const [isWaking, setIsWaking] = useState(false)

  useEffect(() => {
    let active = true
    const timer = window.setTimeout(() => setIsWaking(true), WAKING_NOTICE_DELAY_MS)

    void wakeBackend().finally(() => {
      window.clearTimeout(timer)
      if (active) setIsWaking(false)
    })

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [])

  return isWaking
}
