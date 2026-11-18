import { computed, inject, provide, ref, type InjectionKey } from 'vue'

/**
 * "Vratka" selection of an outbound order: while the selection mode is on, the user
 * collects how much of which row is to be taken back. Nothing is sent to the backend
 * until the whole batch is applied.
 */
const createReturnSelection = () => {
  const active = ref(false)
  /** row index -> amount to take back */
  const batch = ref<Record<number, number>>({})

  const amountOf = (index: number) => batch.value[index] ?? 0
  const set = (index: number, amount: number) => {
    if (amount > 0) {
      batch.value = { ...batch.value, [index]: amount }
    } else {
      remove(index)
    }
  }
  const remove = (index: number) => {
    batch.value = Object.fromEntries(
      Object.entries(batch.value).filter(([key]) => Number(key) !== index),
    )
  }
  const clear = () => {
    batch.value = {}
  }
  /** Leave the selection mode, dropping the batch. */
  const reset = () => {
    clear()
    active.value = false
  }

  const lines = computed(() =>
    Object.entries(batch.value).map(([index, amount]) => ({
      item_index: Number(index),
      amount,
    })),
  )
  const count = computed(() => lines.value.length)

  return { active, batch, amountOf, set, remove, clear, reset, lines, count }
}

export type ReturnSelection = ReturnType<typeof createReturnSelection>

const RETURN_SELECTION_KEY: InjectionKey<ReturnSelection> = Symbol('outbound-return-selection')

export const provideReturnSelection = (): ReturnSelection => {
  const selection = createReturnSelection()
  provide(RETURN_SELECTION_KEY, selection)
  return selection
}

/** The selection of the surrounding order, `null` where returns are not supported. */
export const useReturnSelection = (): ReturnSelection | null => inject(RETURN_SELECTION_KEY, null)

/** States of an order whose goods have left the warehouse - the goods can come back. */
export const RETURNABLE_ORDER_STATES = [
  'sent',
  'completed',
  'invoiced',
  'waiting_for_payment',
  'completed_paid',
]

type ReturnableItem = {
  amount: number
  returned_amount?: number
  is_returned?: boolean
  product: { non_physical?: boolean }
}

/** How much of a sold row can still be taken back. */
export const returnableAmount = (item: ReturnableItem): number =>
  item.is_returned || item.product.non_physical
    ? 0
    : Math.max(0, +(item.amount - (item.returned_amount ?? 0)).toFixed(4))
