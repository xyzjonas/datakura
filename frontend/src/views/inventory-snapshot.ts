import type {
  InventorySnapshotCurrencyTotal,
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

const collator = new Intl.Collator()

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

export const sortSnapshotLines = (lines: InventorySnapshotLineSchema[]) => {
  return lines
    .map((line) => ({ line, key: `${line.product_code}:${line.location_code}:${line.id}` }))
    .sort((left, right) => collator.compare(left.key, right.key))
    .map(({ line }) => line)
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
  lines: InventorySnapshotLineSchema[],
): InventorySnapshotProductGroup[] => {
  type Accumulator = {
    group: InventorySnapshotProductGroup
    purchase: Map<string, number>
    receipt: Map<string, number>
  }
  const accumulators = new Map<string, Accumulator>()

  // totals are accumulated per group and turned into the output shape once at the end
  for (const line of sortSnapshotLines(lines)) {
    let accumulator = accumulators.get(line.product_code)
    if (!accumulator) {
      accumulator = {
        group: {
          productCode: line.product_code,
          productName: line.product_name,
          unitOfMeasure: line.unit_of_measure,
          lines: [],
          itemCount: 0,
          totalQuantity: 0,
          purchase_totals: [],
          receipt_totals: [],
          receipt_unpriced_line_count: 0,
          receiptComplete: true,
        },
        purchase: new Map(),
        receipt: new Map(),
      }
      accumulators.set(line.product_code, accumulator)
    }

    const { group } = accumulator
    group.lines.push(line)
    group.itemCount += 1
    group.totalQuantity += parseAmount(line.quantity) ?? 0
    group.receipt_unpriced_line_count += line.receipt_price_available ? 0 : 1
    addCurrencyTotal(accumulator.purchase, line.purchase_currency, line.purchase_line_value)
    addCurrencyTotal(accumulator.receipt, line.receipt_currency, line.receipt_line_value)
  }

  return [...accumulators.values()]
    .map(({ group, purchase, receipt }) => ({
      ...group,
      purchase_totals: toCurrencyTotals(purchase),
      receipt_totals: toCurrencyTotals(receipt),
      receiptComplete: group.receipt_unpriced_line_count === 0,
    }))
    .sort((left, right) => {
      return collator.compare(
        `${left.productCode}:${left.productName}`,
        `${right.productCode}:${right.productName}`,
      )
    })
}
