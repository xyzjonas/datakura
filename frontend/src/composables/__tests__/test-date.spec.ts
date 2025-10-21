import { afterEach } from 'vitest'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getElapsedTime } from '../use-time-elapsed'

describe('dateUtils', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('getRemainingTime', async () => {
    vi.setSystemTime('2025-08-02 13:30:30')

    expect(getElapsedTime(new Date('2025-08-01 12:00:00'))).toEqual({
      days: 1,
      hours: 1,
      minutes: 30,
      seconds: 30,
    })
  })
})
