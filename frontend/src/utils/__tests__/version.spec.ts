import { beforeEach, describe, expect, it } from 'vitest'
import {
  APP_VERSION,
  CHANGELOG_ENTRIES,
  getInitialLastAcknowledgedVersion,
  getPendingChangelogEntries,
  lastAcknowledgedVersion,
} from '../version'

describe('version utils', () => {
  beforeEach(() => {
    localStorage.clear()
    lastAcknowledgedVersion.value = getInitialLastAcknowledgedVersion()
  })

  it('defaults acknowledged version to previous release when storage is empty', () => {
    expect(lastAcknowledgedVersion.value).toBe(CHANGELOG_ENTRIES[1]?.version)
  })

  it('returns only entries newer than acknowledged version', () => {
    expect(getPendingChangelogEntries('0.0.1dev0')).toEqual([CHANGELOG_ENTRIES[0]])
  })

  it('returns no entries when current version is already acknowledged', () => {
    expect(getPendingChangelogEntries(APP_VERSION)).toEqual([])
  })

  it('returns all tracked entries for unknown versions', () => {
    expect(getPendingChangelogEntries('0.0.0')).toEqual(CHANGELOG_ENTRIES)
  })
})
