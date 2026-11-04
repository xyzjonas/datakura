import { describe, expect, it } from 'vitest'
import type { InventorySnapshotLineSchema } from '@/client'

import {
  formatInventorySnapshotCadence,
  formatInventorySnapshotTriggerSource,
  formatSnapshotTotals,
  groupSnapshotLinesByProduct,
  getSnapshotCoverageLabel,
  getSnapshotLineCurrency,
  getSnapshotLineUnitPrice,
  getSnapshotLineValue,
  isReceiptValuationPartial,
} from '@/views/inventory-snapshot'

const snapshot = {
  purchase_totals: [
    { currency: 'CZK', value: '120.0000' },
    { currency: 'EUR', value: '10.0000' },
  ],
  receipt_totals: [{ currency: 'CZK', value: '95.0000' }],
  receipt_unpriced_line_count: 2,
  trigger_source: 'scheduled',
  cadence: 'monthly',
}

const line: InventorySnapshotLineSchema = {
  id: 1,
  warehouse_item_id: 10,
  warehouse_item_id_at_snapshot: 10,
  product_code: 'SKU-1',
  product_name: 'Produkt',
  location_code: 'A-01',
  quantity: '2.0000',
  unit_of_measure: 'ks',
  tracking_level: 'FUNGIBLE',
  purchase_currency: 'CZK',
  purchase_unit_price: '12.0000',
  purchase_line_value: '24.0000',
  receipt_currency: 'EUR',
  receipt_unit_price: '10.5000',
  receipt_line_value: '21.0000',
  receipt_price_available: true,
}

const missingReceiptLine: InventorySnapshotLineSchema = {
  ...line,
  id: 2,
  warehouse_item_id_at_snapshot: 11,
  location_code: 'A-02',
  receipt_currency: null,
  receipt_unit_price: null,
  receipt_line_value: null,
  receipt_price_available: false,
}

const lines = [line, missingReceiptLine]

describe('inventory snapshot helpers', () => {
  it('formats totals by valuation mode', () => {
    const purchaseTotals = formatSnapshotTotals(snapshot, 'purchase')
    const receiptTotals = formatSnapshotTotals(snapshot, 'receipt')

    expect(purchaseTotals).toContain('120,00')
    expect(purchaseTotals).toContain('Kč')
    expect(purchaseTotals).toContain('10,00')
    expect(purchaseTotals).toContain('€')
    expect(receiptTotals).toContain('95,00')
    expect(receiptTotals).toContain('Kč')
  })

  it('reports partial receipt coverage', () => {
    expect(isReceiptValuationPartial(snapshot)).toBe(true)
    expect(getSnapshotCoverageLabel(snapshot)).toBe('Chybí 2 ř.')
  })

  it('formats trigger and cadence labels', () => {
    expect(formatInventorySnapshotTriggerSource(snapshot.trigger_source)).toBe('Plánovaný')
    expect(formatInventorySnapshotCadence(snapshot.cadence)).toBe('Měsíční')
  })

  it('picks purchase and receipt values per line', () => {
    expect(getSnapshotLineCurrency(line, 'purchase')).toBe('CZK')
    expect(getSnapshotLineCurrency(line, 'receipt')).toBe('EUR')
    expect(getSnapshotLineUnitPrice(line, 'purchase')).toBe('12.0000')
    expect(getSnapshotLineUnitPrice(line, 'receipt')).toBe('10.5000')
    expect(getSnapshotLineValue(line, 'purchase')).toBe('24.0000')
    expect(getSnapshotLineValue(line, 'receipt')).toBe('21.0000')
  })

  it('groups snapshot lines by stock product', () => {
    const groups = groupSnapshotLinesByProduct(lines)

    expect(groups).toHaveLength(1)
    expect(groups[0].productCode).toBe('SKU-1')
    expect(groups[0].itemCount).toBe(2)
    expect(groups[0].totalQuantity).toBe(4)
    expect(groups[0].purchase_totals).toEqual([{ currency: 'CZK', value: '48.0000' }])
    expect(groups[0].receipt_unpriced_line_count).toBe(1)
  })

  it('groups many lines of several products and currencies in one pass', () => {
    const many: InventorySnapshotLineSchema[] = []
    for (let i = 0; i < 300; i++) {
      many.push({
        ...line,
        id: i + 1,
        product_code: `SKU-${i % 3}`,
        product_name: `Produkt ${i % 3}`,
        location_code: `L-${i}`,
        quantity: '1.0000',
        purchase_currency: i % 2 ? 'EUR' : 'CZK',
        purchase_line_value: '2.0000',
        // every 5th line has no receipt
        ...(i % 5 === 0
          ? {
              receipt_currency: null,
              receipt_line_value: null,
              receipt_unit_price: null,
              receipt_price_available: false,
            }
          : { receipt_currency: 'CZK', receipt_line_value: '3.0000' }),
      })
    }

    const groups = groupSnapshotLinesByProduct(many)

    expect(groups.map((g) => g.productCode)).toEqual(['SKU-0', 'SKU-1', 'SKU-2'])
    for (const group of groups) {
      expect(group.itemCount).toBe(100)
      expect(group.lines).toHaveLength(100)
      expect(group.totalQuantity).toBe(100)
      expect(group.receipt_unpriced_line_count).toBe(
        group.lines.filter((l) => !l.receipt_price_available).length,
      )
      expect(group.receiptComplete).toBe(false)
    }
    const total = (rows: { currency: string; value: string }[], currency: string) =>
      Number(rows.find((row) => row.currency === currency)?.value ?? 0)
    // purchase totals stay split by currency and add up to the whole snapshot
    expect(groups.reduce((sum, g) => sum + total(g.purchase_totals, 'CZK'), 0)).toBe(300)
    expect(groups.reduce((sum, g) => sum + total(g.purchase_totals, 'EUR'), 0)).toBe(300)
    expect(groups.reduce((sum, g) => sum + total(g.receipt_totals, 'CZK'), 0)).toBe(240 * 3)
  })

  it('handles snapshots without lines', () => {
    expect(groupSnapshotLinesByProduct([])).toEqual([])
  })

  it('marks a group complete when every line has a receipt price', () => {
    const [group] = groupSnapshotLinesByProduct([line])
    expect(group?.receiptComplete).toBe(true)
    expect(group?.receipt_unpriced_line_count).toBe(0)
  })
})
