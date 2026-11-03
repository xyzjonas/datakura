import { describe, expect, it } from 'vitest'
import { toCertificationMultipartBody } from '../certification-upload'

describe('toCertificationMultipartBody', () => {
  const pdf = new File(['%PDF-1.4'], 'cert.pdf', { type: 'application/pdf' })

  it('includes the attachment next to the form fields', () => {
    const result = toCertificationMultipartBody({ code: 'EN-10204', description: 'd' }, pdf)

    expect(result).toEqual({ code: 'EN-10204', description: 'd', attachment: pdf })
  })

  it.each([
    ['null', null],
    ['undefined', undefined],
  ])('omits the attachment when it is %s', (_label, file) => {
    const result = toCertificationMultipartBody({ code: 'X' }, file)

    expect(result).toEqual({ code: 'X' })
    expect('attachment' in result).toBe(false)
  })

  it('drops empty / nullish fields so they are not sent as "null" strings', () => {
    const result = toCertificationMultipartBody(
      { code: 'X', description: '', certification_id: null },
      null,
    )

    expect(result).toEqual({ code: 'X' })
  })

  it('keeps certification_id 0-safe numeric values', () => {
    expect(toCertificationMultipartBody({ certification_id: 7 }, null)).toEqual({
      certification_id: 7,
    })
  })
})
