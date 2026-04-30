import { useLocalStorage } from '@vueuse/core'
import { computed } from 'vue'

export type ChangelogEntry = {
  version: string
  releaseDate?: string
  rows: string[]
}

export const APP_VERSION = '0.0.1dev1'
export const STORAGE_KEY = 'app-last-acknowledged-version'

export const CHANGELOG_ENTRIES: ChangelogEntry[] = [
  {
    version: '0.0.1dev1',
    releaseDate: '2024-06-30',
    rows: [
      'Přidána možnost ukládání skladových snapshotů (stav skladu v konkrétním okamžiku).',
      'Přidána možnost filtrování přijatých objednávek podle zákazníka.',
      'Přidána možnost nastavení výchozí tiskárny pro tisk dokladů.',
      'Oprava: vydané objednávky je možné libovolně editovat dokud není vytvořen skladový doklad (příjemka).',
      'Oprava: správné načtení aplikace po přihlášení, už není potřeba vždy manuálně obnovit (refresh) stránku.',
    ],
  },
]

export const useVersion = () => {
  const lastAcknowledgedVersion = useLocalStorage<string>(STORAGE_KEY, '')

  const getPendingChangelogEntries = (acknowledgedVersion?: string | null) => {
    if (!acknowledgedVersion) {
      return CHANGELOG_ENTRIES
    }

    const lastAcknowledgedIndex = CHANGELOG_ENTRIES.findIndex(
      ({ version }) => version === acknowledgedVersion,
    )

    if (lastAcknowledgedIndex === 0) {
      return []
    }

    if (lastAcknowledgedIndex === -1) {
      return CHANGELOG_ENTRIES
    }

    return CHANGELOG_ENTRIES.slice(0, lastAcknowledgedIndex)
  }

  const pendingChangelogEntries = computed(() =>
    getPendingChangelogEntries(lastAcknowledgedVersion.value),
  )

  const syncLatestAcknowledgedVersion = () => {
    lastAcknowledgedVersion.value = APP_VERSION
  }

  return {
    lastAcknowledgedVersion,
    pendingChangelogEntries,
    syncLatestAcknowledgedVersion,
  }
}
