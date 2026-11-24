import type { LegendEntrySchema } from '@/client'

/** Name of the loop variable the inserted snippets use. */
export const LOOP_VARIABLE = 'item'

/**
 * Template snippet for a legend entry:
 *  - `order.code`                  -> `{{ order.code }}`
 *  - list `order.items`            -> a for-loop over it
 *  - list `sections[].items`       -> a for-loop over `item.items` (nested loop)
 *  - `order.items[].product.name`  -> `{{ item.product.name }}` (inside such a loop)
 */
export const snippetFor = (entry: Pick<LegendEntrySchema, 'path' | 'type'>): string => {
  const lastList = entry.path.lastIndexOf('[]')
  // below a list the path is relative to the loop variable
  const reference =
    lastList === -1 ? entry.path : `${LOOP_VARIABLE}${entry.path.slice(lastList + 2)}`
  return entry.type === 'list' ? loopOver(reference) : `{{ ${reference} }}`
}

const loopOver = (path: string) => `{% for ${LOOP_VARIABLE} in ${path} %}\n  \n{% endfor %}`
