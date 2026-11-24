import { describe, expect, it } from 'vitest'

import { snippetFor } from '../template-snippets'

describe('snippetFor', () => {
  it.each([
    [{ path: 'order.code', type: 'text' }, '{{ order.code }}'],
    [{ path: 'order', type: 'object' }, '{{ order }}'],
    [{ path: 'order.items[].product.name', type: 'text' }, '{{ item.product.name }}'],
    [{ path: 'order.items[].product', type: 'object' }, '{{ item.product }}'],
    [
      { path: 'order_sections[].order.items[].total_price', type: 'number' },
      '{{ item.total_price }}',
    ],
  ])('%j -> %s', (entry, expected) => {
    expect(snippetFor(entry)).toBe(expected)
  })

  it.each([
    [{ path: 'order.items', type: 'list' }, 'order.items'],
    [{ path: 'order_sections[].order.items', type: 'list' }, 'item.order.items'],
  ])('list %j becomes a for loop', (entry, over) => {
    const snippet = snippetFor(entry)

    expect(snippet).toContain('{% for item in ')
    expect(snippet).toContain('{% endfor %}')
    // `[]` is legend notation, never valid template syntax
    expect(snippet).toContain(` in ${over} %}`)
    expect(snippet).not.toContain('[]')
  })
})
