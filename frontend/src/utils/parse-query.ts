export function parseQueryArray(
  param: string | (string | null | undefined)[] | undefined,
  fallback: string[] = [],
): string[] {
  if (!param) return fallback
  if (Array.isArray(param)) {
    return param
      .filter((p): p is string => typeof p === 'string')
      .flatMap((p) => p.split(',').map((s) => s.trim()))
  }
  return param.split(',').map((s) => s.trim())
}

export function stringifyQueryArray(arr: string[]): string {
  return arr.join(',')
}
