import { useLocalStorage } from '@vueuse/core'
import { computed } from 'vue'

export type ChangelogEntry = {
  version: string
  releaseDate?: string
  rows: string[]
}

export const APP_VERSION = '0.0.1dev5'
export const STORAGE_KEY = 'app-last-acknowledged-version'

export const CHANGELOG_ENTRIES: ChangelogEntry[] = [
  {
    version: '0.0.1dev5',
    releaseDate: '2026-06-11',
    rows: [
      'Přidána možnost libovolného přesunu zboží mezi skladovými místy (nejen přesun pomocí čárového kódu).',
      'Zobrazení nedávných pohybů zboží na domovské stránce (widget "Nedávné pohyby zboží").',
      'Oprava widgetů statistiky.',
    ],
  },
  {
    version: '0.0.1dev4',
    releaseDate: '2026-05-19',
    rows: [
      'Vylepšené vyhledávání produktů při výdeji zboží (výdejka), přehlednější zobrazení variant a jejich skladových zásob.',
      'Přidána možnost správy šarží. Šarže lze přiřazovat ke VŠEM typům skladových položek a následně filtrovat při výdeji zboží (výdejka).',
      'Nastavení monitoringu (Sentry).',
    ],
  },
  {
    version: '0.0.1dev3',
    releaseDate: '2026-05-14',
    rows: [
      'Koncept vydané objednávky se nyní nazývá "Kalkulace" a má svoji vlastní číselnou řadu.',
      'Přidána správa čárových kódů pro produkty, včetně možnosti nastavení primárního čárového kódu (např. pro tisk).',
      '[preview] Úprava dialogu pro vydávání zboží (výdejka), vyhledávání produktů nyní probíhá podle kódu + částečný výdej.',
    ],
  },
  {
    version: '0.0.1dev2',
    releaseDate: '2026-05-07',
    rows: [
      'Přidána možnost zakázání slevových skupin pro konkrétní produkt.',
      'Sledování ceny při výdeji zboží (cena zboží v okamžiku, kdy je skladová položka přiřazena).',
      'Oprava: přijaté objednávky je možné libovolně editovat dokud není daná objednávka vyfakturována.',
    ],
  },
  {
    version: '0.0.1dev1',
    releaseDate: '2026-04-30',
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
