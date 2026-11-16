import type { CertificationAttachSchema, CertificationSchema } from '@/client'
import { formDataBodySerializer } from '@/client/client'

/**
 * The generated SDK types url-encoded form bodies and knows nothing about the
 * uploaded file part, so the multipart serializer / body are supplied through
 * the (spread-last) request options of the SDK call.
 */
export type CertificationMultipartBody = CertificationAttachSchema & {
  attachment?: File
}

export const toCertificationMultipartBody = (
  fields: CertificationAttachSchema,
  attachment: File | null | undefined,
): CertificationMultipartBody => {
  const body: CertificationMultipartBody = {}
  for (const [key, value] of Object.entries(fields)) {
    if (value !== null && value !== undefined && value !== '') {
      ;(body as Record<string, unknown>)[key] = value
    }
  }
  if (attachment) {
    body.attachment = attachment
  }
  return body
}

/** Request options turning an SDK call into a multipart/form-data upload. */
export const multipartRequestOptions = {
  ...formDataBodySerializer,
  headers: { 'Content-Type': null },
}

/** State of the "new / existing certificate" input shared by the certificate forms. */
export type CertificationDraft = {
  mode: 'new' | 'existing'
  code: string
  description: string
  file: File | null
  existing: CertificationSchema | null
}

export const emptyCertificationDraft = (): CertificationDraft => ({
  mode: 'new',
  code: '',
  description: '',
  file: null,
  existing: null,
})

/** Multipart body of the draft, `null` while it is not complete enough to be submitted. */
export const certificationDraftToBody = (
  draft: CertificationDraft,
): CertificationMultipartBody | null => {
  if (draft.mode === 'existing') {
    return draft.existing
      ? toCertificationMultipartBody({ certification_id: draft.existing.id }, null)
      : null
  }
  if (!draft.code.trim() || !draft.file) {
    return null
  }
  return toCertificationMultipartBody(
    { code: draft.code, description: draft.description },
    draft.file,
  )
}
