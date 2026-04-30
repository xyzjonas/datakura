import { useLocalStorage } from '@vueuse/core'

export type ChangelogEntry = {
  version: string
  releaseDate?: string
  rows: string[]
}

export const APP_VERSION = '0.0.1dev1'
export const LAST_ACKNOWLEDGED_VERSION_STORAGE_KEY = 'app-last-acknowledged-version'

export const CHANGELOG_ENTRIES: ChangelogEntry[] = [
  {
    version: APP_VERSION,
    releaseDate: '2024-06-30',
    rows: [
      'Přidána možnost ukládání skladových snapshotů (stav skladu v konkrétním okamžiku).',
      'Přidána možnost filtrování přijatých objednávek podle zákazníka.',
      'Oprava: vydané objednávky je možné libovolně editovat dokud není vystvořen skladový doklad (příjemka)',
    ],
  },
  {
    version: '0.0.1dev0',
    releaseDate: '2024-06-29',
    rows: ['Initial release.'],
  },
]

export const getInitialLastAcknowledgedVersion = () =>
  CHANGELOG_ENTRIES[1]?.version ?? CHANGELOG_ENTRIES[0]?.version ?? APP_VERSION

export const getPendingChangelogEntries = (lastAcknowledgedVersion?: string | null) => {
  if (!lastAcknowledgedVersion) {
    return CHANGELOG_ENTRIES
  }

  const lastAcknowledgedIndex = CHANGELOG_ENTRIES.findIndex(
    ({ version }) => version === lastAcknowledgedVersion,
  )

  if (lastAcknowledgedIndex === 0) {
    return []
  }

  if (lastAcknowledgedIndex === -1) {
    return CHANGELOG_ENTRIES
  }

  return CHANGELOG_ENTRIES.slice(0, lastAcknowledgedIndex)
}

export const lastAcknowledgedVersion = useLocalStorage<string>(
  LAST_ACKNOWLEDGED_VERSION_STORAGE_KEY,
  getInitialLastAcknowledgedVersion(),
)
