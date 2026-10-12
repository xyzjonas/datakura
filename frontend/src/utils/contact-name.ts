import type { ContactPersonSchema } from '@/client'

export const contactFullName = (
  contact: Pick<
    ContactPersonSchema,
    'title_pre' | 'first_name' | 'middle_name' | 'last_name' | 'title_post'
  >,
): string =>
  [
    contact.title_pre,
    contact.first_name,
    contact.middle_name,
    contact.last_name,
    contact.title_post,
  ]
    .filter(Boolean)
    .join(' ')
