import { useMediaQuery } from '@vueuse/core'

/** Order item rows collapse into cards below this viewport width (px). */
export const ORDER_ITEM_CARD_BREAKPOINT = 1400

/** True when the viewport is narrower than the table layout can handle. */
export const useOrderItemCardLayout = () =>
  useMediaQuery(`(max-width: ${ORDER_ITEM_CARD_BREAKPOINT - 1}px)`)
