import type {
  FooterBlockSchema,
  HeaderBlockSchema,
  ItemsBlockSchema,
  LogoBlockSchema,
  PaginationSchema,
  PartyBlockSchema,
} from '@/client'

/** The layout as the API returns it: every block and each of its options is present. */
export interface DocumentLayout {
  logo: Required<LogoBlockSchema>
  header: Required<HeaderBlockSchema>
  supplier: Required<PartyBlockSchema>
  customer: Required<PartyBlockSchema>
  items: Required<ItemsBlockSchema>
  footer: Required<FooterBlockSchema>
  pagination: Required<PaginationSchema>
}
