import { useTimestamp } from '@vueuse/core'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

type ElapsedTime = {
  days: number
  hours: number
  minutes: number
  seconds: number
}

export const getElapsedTime = (then: Date, now?: Date): ElapsedTime => {
  const current = now ?? new Date()
  const deltaSecs = Math.floor((current.getTime() - then.getTime()) / 1000)

  let days = Math.floor(deltaSecs / (24 * 3600))
  let hours = Math.floor((deltaSecs % (24 * 3600)) / 3600)
  let minutes = Math.floor((deltaSecs % 3600) / 60)
  let seconds = deltaSecs % 60

  if (days < 0) {
    days = 0
  }

  if (hours < 0) {
    hours = 0
  }

  if (minutes < 0) {
    minutes = 0
  }

  if (seconds < 0) {
    seconds = 0
  }

  return { days, hours, minutes, seconds }
}

export const useTimeRemaining = (date: MaybeRefOrGetter<Date>) => {
  const timestamp = useTimestamp({ interval: 1000 })

  const elapsed = computed<ElapsedTime>(() =>
    getElapsedTime(toValue(date), new Date(timestamp.value)),
  )

  return {
    elapsed,
  }
}
