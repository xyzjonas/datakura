export const formatDateLong = (date: string | Date) => {
  return new Date(date).toLocaleDateString(undefined, {
    day: '2-digit',
    month: 'long',
    weekday: 'short',
  })
}
