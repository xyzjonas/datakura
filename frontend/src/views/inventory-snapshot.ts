import type {
  InventorySnapshotCurrencyTotal,
  InventorySnapshotDetailSchema,
  InventorySnapshotLineSchema,
} from '@/client'
import { formatCurrency, parseAmount } from '@/utils/format-number'

export type InventorySnapshotValuationMode = 'purchase' | 'receipt'

export type InventorySnapshotCoverageLike = {
  receipt_unpriced_line_count: number
}

export type InventorySnapshotTotalsLike = {
  purchase_totals: InventorySnapshotCurrencyTotal[]
  receipt_totals: InventorySnapshotCurrencyTotal[]
}

export type InventorySnapshotProductGroup = {
  productCode: string
  productName: string
  unitOfMeasure: string
  lines: InventorySnapshotLineSchema[]
  itemCount: number
  totalQuantity: number
  purchase_totals: InventorySnapshotCurrencyTotal[]
  receipt_totals: InventorySnapshotCurrencyTotal[]
  receipt_unpriced_line_count: number
  receiptComplete: boolean
}

const cadenceLabels: Record<string, string> = {
  daily: 'Denní',
  monthly: 'Měsíční',
}

const triggerLabels: Record<string, string> = {
  manual: 'Ruční',
  scheduled: 'Plánovaný',
}

export const formatMoney = (value: string | number | null | undefined) => {
  return formatCurrency(value)
}

export const getSnapshotTotals = (
  snapshot: InventorySnapshotTotalsLike,
  valuationMode: InventorySnapshotValuationMode,
): InventorySnapshotCurrencyTotal[] => {
  return valuationMode === 'purchase' ? snapshot.purchase_totals : snapshot.receipt_totals
}

export const formatSnapshotTotals = (
  snapshot: InventorySnapshotTotalsLike,
  valuationMode: InventorySnapshotValuationMode,
) => {
  const totals = getSnapshotTotals(snapshot, valuationMode)
  if (totals.length === 0) {
    return '—'
  }

  return totals.map((row) => `${formatCurrency(row.value, row.currency)}`).join(' / ')
}

export const isReceiptValuationPartial = (snapshot: InventorySnapshotCoverageLike) => {
  return snapshot.receipt_unpriced_line_count > 0
}

export const formatInventorySnapshotTriggerSource = (triggerSource: string) => {
  return triggerLabels[triggerSource] ?? triggerSource
}

export const formatInventorySnapshotCadence = (cadence?: string | null) => {
  if (!cadence) {
    return '—'
  }

  return cadenceLabels[cadence] ?? cadence
}

export const getSnapshotLineCurrency = (
  line: InventorySnapshotLineSchema,
  valuationMode: InventorySnapshotValuationMode,
) => {
  if (valuationMode === 'purchase') {
    return line.purchase_currency
  }

  return line.receipt_currency ?? '—'
}

export const getSnapshotLineUnitPrice = (
  line: InventorySnapshotLineSchema,
  valuationMode: InventorySnapshotValuationMode,
) => {
  if (valuationMode === 'purchase') {
    return line.purchase_unit_price
  }

  return line.receipt_unit_price
}

export const getSnapshotLineValue = (
  line: InventorySnapshotLineSchema,
  valuationMode: InventorySnapshotValuationMode,
) => {
  if (valuationMode === 'purchase') {
    return line.purchase_line_value
  }

  return line.receipt_line_value
}

export const getSnapshotCoverageLabel = (snapshot: InventorySnapshotCoverageLike) => {
  if (!isReceiptValuationPartial(snapshot)) {
    return 'Příjem kompletní'
  }

  return `Chybí ${snapshot.receipt_unpriced_line_count} ř.`
}

export const getSnapshotCoverageTone = (snapshot: InventorySnapshotCoverageLike) => {
  return isReceiptValuationPartial(snapshot) ? 'warning' : 'positive'
}

export const sortSnapshotLines = (snapshot: InventorySnapshotDetailSchema) => {
  return [...snapshot.lines].sort((left, right) => {
    return `${left.product_code}:${left.location_code}:${left.id}`.localeCompare(
      `${right.product_code}:${right.location_code}:${right.id}`,
    )
  })
}

const addCurrencyTotal = (
  totalsByCurrency: Map<string, number>,
  currency: string | null | undefined,
  value: string | null | undefined,
) => {
  if (!currency || !value) {
    return
  }

  const parsedValue = parseAmount(value)
  if (parsedValue === null) {
    return
  }

  totalsByCurrency.set(currency, (totalsByCurrency.get(currency) ?? 0) + parsedValue)
}

const toCurrencyTotals = (
  totalsByCurrency: Map<string, number>,
): InventorySnapshotCurrencyTotal[] => {
  return [...totalsByCurrency.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([currency, value]) => ({
      currency,
      value: value.toFixed(4),
    }))
}

export const groupSnapshotLinesByProduct = (
  snapshot: InventorySnapshotDetailSchema,
): InventorySnapshotProductGroup[] => {
  const groups = new Map<string, InventorySnapshotProductGroup>()

  for (const line of sortSnapshotLines(snapshot)) {
    const existing = groups.get(line.product_code)
    if (existing) {
      existing.lines.push(line)
      existing.itemCount += 1
      existing.totalQuantity += parseAmount(line.quantity) ?? 0

      const purchaseTotals = new Map(
        existing.purchase_totals.map((row) => [row.currency, Number.parseFloat(String(row.value))]),
      )
      const receiptTotals = new Map(
        existing.receipt_totals.map((row) => [row.currency, Number.parseFloat(String(row.value))]),
      )

      addCurrencyTotal(purchaseTotals, line.purchase_currency, line.purchase_line_value)
      addCurrencyTotal(receiptTotals, line.receipt_currency, line.receipt_line_value)

      existing.purchase_totals = toCurrencyTotals(purchaseTotals)
      existing.receipt_totals = toCurrencyTotals(receiptTotals)
      existing.receipt_unpriced_line_count += line.receipt_price_available ? 0 : 1
      existing.receiptComplete = existing.receipt_unpriced_line_count === 0
      continue
    }

    const purchaseTotals = new Map<string, number>()
    const receiptTotals = new Map<string, number>()
    addCurrencyTotal(purchaseTotals, line.purchase_currency, line.purchase_line_value)
    addCurrencyTotal(receiptTotals, line.receipt_currency, line.receipt_line_value)

    groups.set(line.product_code, {
      productCode: line.product_code,
      productName: line.product_name,
      unitOfMeasure: line.unit_of_measure,
      lines: [line],
      itemCount: 1,
      totalQuantity: parseAmount(line.quantity) ?? 0,
      purchase_totals: toCurrencyTotals(purchaseTotals),
      receipt_totals: toCurrencyTotals(receiptTotals),
      receipt_unpriced_line_count: line.receipt_price_available ? 0 : 1,
      receiptComplete: line.receipt_price_available,
    })
  }

  return [...groups.values()].sort((left, right) => {
    return `${left.productCode}:${left.productName}`.localeCompare(
      `${right.productCode}:${right.productName}`,
    )
  })
}

export const filterSnapshotProductGroups = (
  groups: InventorySnapshotProductGroup[],
  searchTerm: string,
) => {
  const normalizedSearch = searchTerm.trim().toLowerCase()
  if (!normalizedSearch) {
    return groups
  }

  return groups.filter((group) => {
    return (
      group.productCode.toLowerCase().includes(normalizedSearch) ||
      group.productName.toLowerCase().includes(normalizedSearch)
    )
  })
}
