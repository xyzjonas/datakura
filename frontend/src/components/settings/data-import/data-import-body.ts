import type { WarehouseApiRoutesDataImportStartDataImportData } from '@/client'

export type DataImportFormBody = WarehouseApiRoutesDataImportStartDataImportData['body']

export type WarehouseImportRowModel = {
  key: number
  warehouse: string
  file: File | null
}

export type DataImportFormState = {
  productsFile: File | null
  customersFile: File | null
  warehouseRows: WarehouseImportRowModel[]
}

export const isWarehouseRowComplete = (row: WarehouseImportRowModel): boolean =>
  row.warehouse.trim() !== '' && row.file !== null

/** Completely untouched row - ignored on submit instead of blocking it */
export const isWarehouseRowEmpty = (row: WarehouseImportRowModel): boolean =>
  row.warehouse.trim() === '' && row.file === null

export const hasIncompleteRows = (rows: WarehouseImportRowModel[]): boolean =>
  rows.some((row) => !isWarehouseRowEmpty(row) && !isWarehouseRowComplete(row))

export const canSubmitDataImport = (state: DataImportFormState): boolean => {
  if (hasIncompleteRows(state.warehouseRows)) {
    return false
  }
  return (
    state.productsFile !== null ||
    state.customersFile !== null ||
    state.warehouseRows.some(isWarehouseRowComplete)
  )
}

/** Warehouse ids and files are paired by position on the backend */
export const toDataImportBody = (state: DataImportFormState): DataImportFormBody => {
  const rows = state.warehouseRows.filter(isWarehouseRowComplete)
  return {
    products_file: state.productsFile ?? undefined,
    customers_file: state.customersFile ?? undefined,
    warehouse_ids: rows.map((row) => row.warehouse.trim()),
    warehouse_files: rows.map((row) => row.file as File),
  }
}
