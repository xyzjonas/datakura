import { CompletionContext } from '@codemirror/autocomplete'
import { EditorState } from '@codemirror/state'
import { describe, expect, it } from 'vitest'

import type { DocumentLegendSchema } from '@/client'
import { createTemplateCompletion, insideExpression } from '../template-completions'

const legend: DocumentLegendSchema = {
  fields: [
    { path: 'order', type: 'object' },
    { path: 'order.code', type: 'text' },
    { path: 'order.items', type: 'list' },
    { path: 'order.items[].product.name', type: 'text' },
  ],
  filters: [{ name: 'date', signature: 'date(fmt)', description: 'Formats a date' }],
}

// `^` in the doc marks the cursor
const complete = (docWithCursor: string, explicit = false, withLegend = true) => {
  const pos = docWithCursor.indexOf('^')
  const doc = docWithCursor.replace('^', '')
  const context = new CompletionContext(EditorState.create({ doc }), pos, explicit)
  return createTemplateCompletion(() => (withLegend ? legend : undefined))(context)
}

describe('insideExpression', () => {
  it.each([
    ['', false],
    ['<p>text', false],
    ['{{ ord', true],
    ['{% for', true],
    ['{{ a }} text', false],
    ['{% if a %} {{ b', true],
    ['{% if a %}', false],
  ])('%j -> %s', (text, expected) => {
    expect(insideExpression(text)).toBe(expected)
  })
})

describe('createTemplateCompletion', () => {
  it('offers context paths inside an expression, without list-item paths', () => {
    const result = complete('<p>{{ ord^')

    expect(result?.options.map((o) => o.label)).toEqual(['order', 'order.code', 'order.items'])
    expect(result?.from).toBe('<p>{{ '.length)
  })

  it('offers nothing in plain html', () => {
    expect(complete('<p>ord^')).toBeNull()
    expect(complete('{{ a }} ord^')).toBeNull()
  })

  it('offers filters after a pipe', () => {
    const result = complete('{{ order.created | da^')

    expect(result?.options.map((o) => o.label)).toEqual(['date'])
  })

  it('offers block keywords after {%', () => {
    const labels = complete('{% fo^')?.options.map((o) => o.label)

    expect(labels).toContain('for')
    expect(labels).toContain('endif')
  })

  it('stays quiet on an empty word unless invoked explicitly', () => {
    expect(complete('{{ ^')).toBeNull()
    expect(complete('{{ ^', true)).not.toBeNull()
  })

  it('does nothing before the legend is loaded', () => {
    expect(complete('{{ ord^', false, false)).toBeNull()
  })
})
