export const formatDateLong = (date?: string | Date | null) => {
  if (!date) {
    return '-'
  }
  return new Date(date).toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'long',
    weekday: 'short',
  })
}

export const formatDateTimeLong = (date: string | Date) => {
  const acutalDate = new Date(date)
  return `${formatDateLong(date)} - ${acutalDate.toLocaleTimeString()}`
}

export const formatDateShort = (value: string) =>
  new Date(value).toLocaleDateString('cs-CZ', {
    month: 'long',
    day: 'numeric',
  })

export const formatDateWithYear = (value?: string | Date | null) =>
  value
    ? new Date(value).toLocaleDateString('cs-CZ', {
        day: 'numeric',
        month: 'numeric',
        year: 'numeric',
      })
    : '-'
