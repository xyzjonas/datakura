export function formatNumber(num: number): string {
  return new Intl.NumberFormat().format(num)
}

export function parseAmount(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) {
    return null
  }

  const parsed = Number.parseFloat(String(value))
  if (Number.isNaN(parsed)) {
    return null
  }

  return parsed
}

export function formatCurrency(
  value: string | number | null | undefined,
  currencyCode: string = 'CZK',
): string {
  const parsed = parseAmount(value)
  if (parsed === null) {
    return '—'
  }

  return Intl.NumberFormat('cs-CZ', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    style: 'currency',
    currency: currencyCode,
  }).format(parsed)
}
