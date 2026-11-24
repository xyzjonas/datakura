import type { CompletionContext, CompletionResult } from '@codemirror/autocomplete'
import type { DocumentLegendSchema } from '@/client'

const BLOCK_KEYWORDS = ['for', 'endfor', 'if', 'elif', 'else', 'endif', 'set', 'endset', 'include']

/** Is the cursor (text before it) inside an unclosed `{{ … }}` / `{% … %}`? */
export const insideExpression = (textBefore: string): boolean => {
  const open = Math.max(textBefore.lastIndexOf('{{'), textBefore.lastIndexOf('{%'))
  const close = Math.max(textBefore.lastIndexOf('}}'), textBefore.lastIndexOf('%}'))
  return open > close
}

/**
 * Autocompletion of the template context: variable paths, filters after `|` and block
 * keywords after `{%`. Paths below a list (`items[]…`) are only offered through the
 * legend, as the loop variable name is up to the template author.
 */
export const createTemplateCompletion =
  (getLegend: () => DocumentLegendSchema | undefined) =>
  (context: CompletionContext): CompletionResult | null => {
    const legend = getLegend()
    if (!legend) return null

    const line = context.state.doc.lineAt(context.pos)
    const textBefore = context.state.doc.sliceString(0, context.pos)
    if (!insideExpression(textBefore)) return null

    const word = context.matchBefore(/[\w.]*/)
    if (!word || (word.from === word.to && !context.explicit)) return null

    const beforeWord = line.text.slice(0, word.from - line.from)

    if (/\|\s*$/.test(beforeWord)) {
      return {
        from: word.from,
        options: legend.filters.map((f) => ({
          label: f.name,
          type: 'function',
          detail: f.signature,
          info: f.description,
        })),
      }
    }

    if (/\{%\s*$/.test(beforeWord)) {
      return {
        from: word.from,
        options: BLOCK_KEYWORDS.map((label) => ({ label, type: 'keyword' })),
      }
    }

    return {
      from: word.from,
      options: legend.fields
        .filter((f) => !f.path.includes('[]'))
        .map((f) => ({
          label: f.path,
          type: f.type === 'object' || f.type === 'list' ? 'namespace' : 'variable',
          detail: f.type,
          info: f.description ?? undefined,
        })),
    }
  }
