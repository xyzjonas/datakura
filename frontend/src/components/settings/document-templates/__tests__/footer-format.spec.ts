import { describe, expect, it } from 'vitest'

import { toggleFormat, type FooterFormat } from '../footer-format'

const sel = (text: string, start: number, end: number) => ({ text, start, end })

describe('toggleFormat', () => {
  it.each<[FooterFormat, ReturnType<typeof sel>, ReturnType<typeof sel>]>([
    ['bold', sel('hello world', 6, 11), sel('hello **world**', 8, 13)],
    ['italic', sel('hello world', 0, 5), sel('*hello* world', 1, 6)],
    ['underline', sel('hello', 0, 5), sel('__hello__', 2, 7)],
    // nothing selected: an empty pair, caret in the middle
    ['bold', sel('ab', 1, 1), sel('a****b', 3, 3)],
    ['italic', sel('', 0, 0), sel('**', 1, 1)],
    // already wrapped (selection includes the markers)
    ['bold', sel('x **y** z', 2, 7), sel('x y z', 2, 3)],
    // already wrapped (selection inside the markers)
    ['italic', sel('x *y* z', 3, 4), sel('x y z', 2, 3)],
    ['underline', sel('__y__', 2, 3), sel('y', 0, 1)],
  ])('%s %j', (format, input, expected) => {
    expect(toggleFormat(input, format)).toEqual(expected)
  })

  it('does not mistake bold markers for italic ones when unwrapping', () => {
    // "**y**" selected with italic: wraps again instead of eating one asterisk of each side
    const result = toggleFormat(sel('**y**', 2, 3), 'italic')

    expect(result.text).toBe('***y***')
  })
})
