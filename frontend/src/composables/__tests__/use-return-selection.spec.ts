import { describe, expect, it } from 'vitest'
import { provideReturnSelection, returnableAmount } from '../use-return-selection'
import { createApp, defineComponent, h } from 'vue'

const makeSelection = () => {
  let selection!: ReturnType<typeof provideReturnSelection>
  const app = createApp(
    defineComponent({
      setup() {
        selection = provideReturnSelection()
        return () => h('div')
      },
    }),
  )
  app.mount(document.createElement('div'))
  return selection
}

describe('return selection', () => {
  it('starts inactive and empty', () => {
    const selection = makeSelection()
    expect(selection.active.value).toBe(false)
    expect(selection.count.value).toBe(0)
    expect(selection.lines.value).toEqual([])
  })

  it('collects amounts per row and replaces an already selected row', () => {
    const selection = makeSelection()
    selection.set(0, 3)
    selection.set(2, 1.5)
    selection.set(0, 5)

    expect(selection.amountOf(0)).toBe(5)
    expect(selection.amountOf(1)).toBe(0)
    expect(selection.lines.value).toEqual([
      { item_index: 0, amount: 5 },
      { item_index: 2, amount: 1.5 },
    ])
    expect(selection.count.value).toBe(2)
  })

  it.each([0, -2])('setting amount %d removes the row from the batch', (amount) => {
    const selection = makeSelection()
    selection.set(1, 4)
    selection.set(1, amount)

    expect(selection.count.value).toBe(0)
  })

  it('removing a row keeps the others', () => {
    const selection = makeSelection()
    selection.set(0, 1)
    selection.set(1, 2)
    selection.remove(0)

    expect(selection.lines.value).toEqual([{ item_index: 1, amount: 2 }])
  })

  it('reset drops the batch and leaves the selection mode', () => {
    const selection = makeSelection()
    selection.active.value = true
    selection.set(0, 1)
    selection.reset()

    expect(selection.active.value).toBe(false)
    expect(selection.count.value).toBe(0)
  })
})

describe('returnableAmount', () => {
  const product = { non_physical: false }
  it.each([
    [{ amount: 10, product }, 10],
    [{ amount: 10, returned_amount: 4, product }, 6],
    [{ amount: 10, returned_amount: 10, product }, 0],
    [{ amount: 0.3, returned_amount: 0.1, product }, 0.2], // no float noise
    [{ amount: 10, is_returned: true, product }, 0],
    [{ amount: 10, product: { non_physical: true } }, 0],
  ])('%j -> %d', (item, expected) => {
    expect(returnableAmount(item)).toBe(expected)
  })
})
