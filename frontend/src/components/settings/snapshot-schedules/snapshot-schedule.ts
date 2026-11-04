import type { SnapshotScheduleCreateOrUpdateSchema, SnapshotScheduleSchema } from '@/client'

// January has 31 days - the calendar only picks a day of the month, the month is irrelevant.
const CALENDAR_YEAR_MONTH = '2024/01'

export const CALENDAR_NAV_YEAR_MONTH = CALENDAR_YEAR_MONTH

export const dayToCalendarDate = (day: number | null | undefined): string =>
  `${CALENDAR_YEAR_MONTH}/${String(day ?? 1).padStart(2, '0')}`

export const calendarDateToDay = (date: string | null): number | null => {
  if (!date) {
    return null
  }
  const day = Number(date.split('/')[2])
  return Number.isNaN(day) ? null : day
}

export const formatTime = (hour: number, minute: number): string =>
  `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`

export const parseTime = (value: string | null): { hour: number; minute: number } | null => {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value ?? '')
  if (!match) {
    return null
  }
  const hour = Number(match[1])
  const minute = Number(match[2])
  return hour > 23 || minute > 59 ? null : { hour, minute }
}

export const describeSchedule = (
  schedule: Pick<SnapshotScheduleSchema, 'mode' | 'day_of_month' | 'hour' | 'minute'>,
): string => {
  const time = formatTime(schedule.hour, schedule.minute)
  return schedule.mode === 'last_day_of_month'
    ? `Poslední den v měsíci v ${time}`
    : `Každého ${schedule.day_of_month}. v měsíci v ${time}`
}

export const createDefaultScheduleForm = (): SnapshotScheduleCreateOrUpdateSchema => ({
  name: '',
  enabled: true,
  mode: 'day_of_month',
  day_of_month: 1,
  hour: 2,
  minute: 0,
})

export const scheduleToForm = (
  schedule: SnapshotScheduleSchema,
): SnapshotScheduleCreateOrUpdateSchema => ({
  name: schedule.name,
  enabled: schedule.enabled,
  mode: schedule.mode,
  day_of_month: schedule.day_of_month ?? 1,
  hour: schedule.hour,
  minute: schedule.minute,
})
