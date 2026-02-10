export const formatDateLong = (date: string | Date) => {
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
