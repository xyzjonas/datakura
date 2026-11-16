import { describe, expect, it } from 'vitest'
import {
  COUNTRY_CODES,
  countryFlag,
  countryName,
  countryOptions,
  filterCountries,
} from '../countries'

describe('countries', () => {
  it('lists all 249 ISO 3166-1 alpha-2 codes once', () => {
    expect(COUNTRY_CODES).toHaveLength(249)
    expect(new Set(COUNTRY_CODES).size).toBe(249)
    expect(COUNTRY_CODES.every((c) => /^[A-Z]{2}$/.test(c))).toBe(true)
    expect(COUNTRY_CODES).toEqual(expect.arrayContaining(['CZ', 'SK', 'DE', 'CN', 'US']))
  })

  it.each([
    ['CZ', 'Česko'],
    ['cz', 'Česko'],
    ['DE', 'Německo'],
  ])('countryName(%s) is localized', (code, expected) => {
    expect(countryName(code)).toBe(expected)
  })

  it.each([null, undefined, ''])('countryName(%s) is empty', (value) => {
    expect(countryName(value)).toBe('')
  })

  it('falls back to the code for unknown / malformed input', () => {
    expect(countryName('1')).toBe('1')
  })

  it.each([
    ['CZ', '🇨🇿'],
    ['de', '🇩🇪'],
    ['', ''],
    [null, ''],
    ['CZE', ''],
    ['1A', ''],
  ])('countryFlag(%s)', (code, expected) => {
    expect(countryFlag(code)).toBe(expected)
  })

  it('options cover every country, sorted by localized name', () => {
    const options = countryOptions()
    expect(options).toHaveLength(249)
    const names = options.map((o) => o.name)
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, 'cs')))
  })

  describe('filterCountries', () => {
    it('returns everything for an empty needle', () => {
      expect(filterCountries('')).toHaveLength(249)
      expect(filterCountries('   ')).toHaveLength(249)
    })

    it.each([
      ['nemec', 'DE'],
      ['Německo', 'DE'],
      ['ČESK', 'CZ'],
      ['cesko', 'CZ'],
      ['slov', 'SK'],
    ])('"%s" finds %s', (needle, code) => {
      expect(filterCountries(needle).map((o) => o.code)).toContain(code)
    })

    it('matches an exact ISO code', () => {
      expect(filterCountries('vn').map((o) => o.code)).toContain('VN')
    })

    it('finds nothing for gibberish', () => {
      expect(filterCountries('qqqqzzzz')).toEqual([])
    })
  })
})
