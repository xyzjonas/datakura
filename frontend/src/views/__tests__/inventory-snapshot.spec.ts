import { describe, expect, it } from 'vitest'
import type { InventorySnapshotLineSchema } from '@/client'

import {
  filterSnapshotProductGroups,
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

const detailSnapshot = {
  id: 1,
  created: '2026-04-28T10:00:00Z',
  changed: '2026-04-28T10:00:00Z',
  captured_at: '2026-04-28T10:00:00Z',
  trigger_source: 'manual',
  cadence: null,
  bucket_key: null,
  line_count: 2,
  purchase_totals: snapshot.purchase_totals,
  receipt_totals: snapshot.receipt_totals,
  receipt_unpriced_line_count: 1,
  receipt_complete: false,
  lines: [line, missingReceiptLine],
}

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
    const groups = groupSnapshotLinesByProduct(detailSnapshot)

    expect(groups).toHaveLength(1)
    expect(groups[0].productCode).toBe('SKU-1')
    expect(groups[0].itemCount).toBe(2)
    expect(groups[0].totalQuantity).toBe(4)
    expect(groups[0].purchase_totals).toEqual([{ currency: 'CZK', value: '48.0000' }])
    expect(groups[0].receipt_unpriced_line_count).toBe(1)
  })

  it('filters grouped products by code or name', () => {
    const groups = groupSnapshotLinesByProduct(detailSnapshot)

    expect(filterSnapshotProductGroups(groups, 'sku-1')).toHaveLength(1)
    expect(filterSnapshotProductGroups(groups, 'produkt')).toHaveLength(1)
    expect(filterSnapshotProductGroups(groups, 'missing')).toHaveLength(0)
  })
})
