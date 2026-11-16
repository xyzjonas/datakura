import { describe, expect, it } from 'vitest'
import {
  certificationDraftToBody,
  emptyCertificationDraft,
  toCertificationMultipartBody,
  type CertificationDraft,
} from '../certification-upload'

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

describe('certificationDraftToBody', () => {
  const pdf = new File(['%PDF-1.4'], 'cert.pdf', { type: 'application/pdf' })
  const draft = (patch: Partial<CertificationDraft>): CertificationDraft => ({
    ...emptyCertificationDraft(),
    ...patch,
  })

  it.each([
    ['empty draft', {}],
    ['new without file', { code: 'C-1' }],
    ['new without code', { file: pdf }],
    ['new with blank code', { code: '  ', file: pdf }],
    ['existing without selection', { mode: 'existing' as const }],
  ])('is not submittable: %s', (_label, patch) => {
    expect(certificationDraftToBody(draft(patch))).toBeNull()
  })

  it('builds the body of a new certificate', () => {
    expect(certificationDraftToBody(draft({ code: 'C-1', description: 'd', file: pdf }))).toEqual({
      code: 'C-1',
      description: 'd',
      attachment: pdf,
    })
  })

  it('builds the body of an existing certificate', () => {
    const existing = { id: 7, code: 'C-7' } as CertificationDraft['existing']

    expect(certificationDraftToBody(draft({ mode: 'existing', existing }))).toEqual({
      certification_id: 7,
    })
  })
})
