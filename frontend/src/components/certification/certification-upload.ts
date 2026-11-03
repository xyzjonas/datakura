import type { CertificationAttachSchema } from '@/client'
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
