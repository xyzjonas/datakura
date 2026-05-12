type AuditPresentationEntry = {
  source?: string | null
  action?: string | null
}

export function normalizeAuditAction(action?: string | null): string {
  return (action ?? '').toString().trim().toLowerCase()
}

export function getAuditEntryColor(entry: AuditPresentationEntry): string {
  const action = normalizeAuditAction(entry.action)

  if (entry.source === 'movement') {
    return 'primary'
  }
  if (action === 'create') {
    return 'positive'
  }
  if (action === 'delete') {
    return 'negative'
  }
  if (action === 'transition') {
    return 'warning'
  }
  return 'grey-7'
}

export function getAuditEntryIcon(entry: AuditPresentationEntry): string {
  if (entry.source === 'movement') {
    return 'swap_horiz'
  }

  const action = normalizeAuditAction(entry.action)
  if (action === 'create') {
    return 'add'
  }
  if (action === 'delete') {
    return 'delete'
  }
  if (action === 'transition') {
    return 'sym_o_double_arrow'
  }
  if (action === 'update') {
    return 'edit'
  }
  return 'history'
}
