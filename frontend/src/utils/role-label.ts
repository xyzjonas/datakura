/** Human readable role from `AuthData.group` (superuser / admin / Django group name / none). */
export const roleLabel = (group?: string | null): string => {
  if (group === 'superuser') {
    return 'Administrátor'
  }
  if (group === 'admin') {
    return 'Správce'
  }
  return group || 'Uživatel'
}
