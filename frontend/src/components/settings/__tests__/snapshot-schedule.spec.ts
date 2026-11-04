import { describe, expect, it } from 'vitest'

import {
  calendarDateToDay,
  createDefaultScheduleForm,
  dayToCalendarDate,
  describeSchedule,
  formatTime,
  parseTime,
  scheduleToForm,
} from '@/components/settings/snapshot-schedules/snapshot-schedule'

describe('snapshot schedule helpers', () => {
  it.each([1, 15, 28, 29, 30, 31])('round-trips day %i through the calendar date', (day) => {
    expect(calendarDateToDay(dayToCalendarDate(day))).toBe(day)
  })

  it('falls back to the first day and ignores empty calendar values', () => {
    expect(dayToCalendarDate(null)).toBe('2024/01/01')
    expect(calendarDateToDay(null)).toBeNull()
    expect(calendarDateToDay('')).toBeNull()
  })

  it.each([
    ['02:05', { hour: 2, minute: 5 }],
    ['23:59', { hour: 23, minute: 59 }],
    ['0:00', { hour: 0, minute: 0 }],
    ['24:00', null],
    ['12:60', null],
    ['', null],
    [null, null],
    ['abc', null],
  ])('parses time %s', (value, expected) => {
    expect(parseTime(value)).toEqual(expected)
  })

  it('formats time with zero padding', () => {
    expect(formatTime(2, 5)).toBe('02:05')
  })

  it('describes both schedule modes', () => {
    expect(describeSchedule({ mode: 'day_of_month', day_of_month: 15, hour: 3, minute: 30 })).toBe(
      'Každého 15. v měsíci v 03:30',
    )
    expect(
      describeSchedule({ mode: 'last_day_of_month', day_of_month: null, hour: 23, minute: 0 }),
    ).toBe('Poslední den v měsíci v 23:00')
  })

  it('builds the edit form from a schedule, defaulting the day for last-day mode', () => {
    expect(createDefaultScheduleForm().mode).toBe('day_of_month')
    expect(
      scheduleToForm({
        id: 1,
        name: 'Konec měsíce',
        enabled: false,
        mode: 'last_day_of_month',
        day_of_month: null,
        hour: 1,
        minute: 2,
        last_run_at: null,
        total_run_count: 4,
      }),
    ).toEqual({
      name: 'Konec měsíce',
      enabled: false,
      mode: 'last_day_of_month',
      day_of_month: 1,
      hour: 1,
      minute: 2,
    })
  })
})
