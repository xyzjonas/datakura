import { describe, expect, it } from 'vitest'

import { roleLabel } from '@/utils/role-label'

describe('roleLabel', () => {
  it.each([
    ['superuser', 'Administrátor'],
    ['admin', 'Správce'],
    ['warehouse', 'warehouse'],
    ['', 'Uživatel'],
    [null, 'Uživatel'],
    [undefined, 'Uživatel'],
  ])('maps %s to %s', (group, expected) => {
    expect(roleLabel(group)).toBe(expected)
  })
})
