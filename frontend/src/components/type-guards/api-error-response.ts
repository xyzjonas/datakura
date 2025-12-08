import type { ErrorInformation } from '@/client'

export const containsCustomError = (
  obj: unknown | string | object | { error: ErrorInformation },
): obj is { error: ErrorInformation } => {
  return typeof obj === 'object' && obj !== null && 'error' in obj && isCustomError(obj.error)
}

export const isCustomError = (
  obj: unknown | string | object | ErrorInformation,
): obj is ErrorInformation => {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'error_code' in obj &&
    'message' in obj &&
    'exception' in obj
  )
}
