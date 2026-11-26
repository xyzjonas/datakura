/** The markers the footer understands (rendered by the API): **bold**, *italic*, __underline__. */
export type FooterFormat = 'bold' | 'italic' | 'underline'

export const FOOTER_MARKERS: Record<FooterFormat, string> = {
  bold: '**',
  italic: '*',
  underline: '__',
}

export interface TextSelection {
  text: string
  start: number
  end: number
}

/**
 * Wraps the selection in the format's marker (or unwraps it when it is already wrapped).
 * With nothing selected, an empty pair is inserted and the caret placed between the markers.
 */
export const toggleFormat = (
  { text, start, end }: TextSelection,
  format: FooterFormat,
): TextSelection => {
  const marker = FOOTER_MARKERS[format]
  const size = marker.length
  const selected = text.slice(start, end)
  const char = marker[0]

  // markers inside the selection: "**abc**" selected
  if (
    selected.length > size * 2 &&
    selected.startsWith(marker) &&
    selected.endsWith(marker) &&
    selected[size] !== char && // "**x**" is bold, not italic
    selected[selected.length - size - 1] !== char
  ) {
    const inner = selected.slice(size, selected.length - size)
    return {
      text: text.slice(0, start) + inner + text.slice(end),
      start,
      end: start + inner.length,
    }
  }
  // markers just around the selection: **[abc]**
  if (
    text.slice(start - size, start) === marker &&
    text.slice(end, end + size) === marker &&
    text[start - size - 1] !== char &&
    text[end + size] !== char
  ) {
    return {
      text: text.slice(0, start - size) + selected + text.slice(end + size),
      start: start - size,
      end: end - size,
    }
  }
  return {
    text: text.slice(0, start) + marker + selected + marker + text.slice(end),
    start: start + size,
    end: end + size,
  }
}
