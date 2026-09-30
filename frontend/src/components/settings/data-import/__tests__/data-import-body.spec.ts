import { describe, expect, it } from 'vitest'

import {
  canSubmitDataImport,
  hasIncompleteRows,
  toDataImportBody,
  type DataImportFormState,
  type WarehouseImportRowModel,
} from '../data-import-body'

const file = (name: string) => new File(['{}'], name, { type: 'application/json' })
const row = (key: number, warehouse: string, f: File | null): WarehouseImportRowModel => ({
  key,
  warehouse,
  file: f,
})
const state = (overrides: Partial<DataImportFormState> = {}): DataImportFormState => ({
  productsFile: null,
  customersFile: null,
  warehouseRows: [],
  ...overrides,
})

describe('canSubmitDataImport', () => {
  it.each([
    ['nothing selected', state(), false],
    ['only products', state({ productsFile: file('p.json') }), true],
    ['only customers', state({ customersFile: file('c.json') }), true],
    ['only a complete warehouse', state({ warehouseRows: [row(0, 'W', file('w.json'))] }), true],
    ['only an untouched warehouse row', state({ warehouseRows: [row(0, '', null)] }), false],
    ['warehouse without file', state({ warehouseRows: [row(0, 'W', null)] }), false],
    ['warehouse file without name', state({ warehouseRows: [row(0, '', file('w.json'))] }), false],
    ['blank-only warehouse name', state({ warehouseRows: [row(0, '   ', file('w.json'))] }), false],
    [
      'valid products but incomplete warehouse',
      state({ productsFile: file('p.json'), warehouseRows: [row(0, 'W', null)] }),
      false,
    ],
    [
      'valid products and an untouched extra row',
      state({ productsFile: file('p.json'), warehouseRows: [row(0, '', null)] }),
      true,
    ],
  ])('%s', (_label, formState, expected) => {
    expect(canSubmitDataImport(formState)).toBe(expected)
  })
})

describe('hasIncompleteRows', () => {
  it('ignores untouched rows and accepts complete ones', () => {
    expect(hasIncompleteRows([row(0, '', null), row(1, 'W', file('w.json'))])).toBe(false)
  })

  it('flags half-filled rows', () => {
    expect(hasIncompleteRows([row(0, 'W', null)])).toBe(true)
  })
})

describe('toDataImportBody', () => {
  it('pairs warehouse ids and files by position, trims names and drops untouched rows', () => {
    const first = file('a.json')
    const second = file('b.json')

    const body = toDataImportBody(
      state({
        warehouseRows: [row(0, ' A ', first), row(1, '', null), row(2, 'B', second)],
      }),
    )

    expect(body.warehouse_ids).toEqual(['A', 'B'])
    expect(body.warehouse_files).toEqual([first, second])
  })

  it('omits sections without file', () => {
    const products = file('p.json')

    const body = toDataImportBody(state({ productsFile: products }))

    expect(body.products_file).toBe(products)
    expect(body.customers_file).toBeUndefined()
    expect(body.warehouse_ids).toEqual([])
    expect(body.warehouse_files).toEqual([])
  })
})
