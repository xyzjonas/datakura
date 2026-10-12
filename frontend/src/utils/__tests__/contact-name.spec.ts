import { describe, expect, it } from 'vitest'
import { contactFullName } from '../contact-name'

describe('contactFullName', () => {
  it('joins all present parts', () => {
    expect(
      contactFullName({
        title_pre: 'Ing.',
        first_name: 'Jan',
        middle_name: 'Karel',
        last_name: 'Novák',
        title_post: 'Ph.D.',
      }),
    ).toBe('Ing. Jan Karel Novák Ph.D.')
  })

  it.each([
    [{ first_name: 'Jan', last_name: 'Novák' }, 'Jan Novák'],
    [{ title_pre: '', first_name: 'Jan', middle_name: null, last_name: 'Novák' }, 'Jan Novák'],
  ])('skips empty parts (%#)', (contact, expected) => {
    expect(contactFullName(contact)).toBe(expected)
  })
})
