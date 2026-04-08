import { nextTick } from 'vue'
import { beforeEach, describe, expect, it } from 'vitest'
import { useDrawer } from '../use-drawer'

describe('useDrawer', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('shares state across composable calls and persists it in localStorage', async () => {
    const first = useDrawer()
    const second = useDrawer()

    expect(first.isOpened.value).toBe(true)
    expect(second.isOpened.value).toBe(true)

    first.close()
    await nextTick()
    expect(first.isOpened.value).toBe(false)
    expect(second.isOpened.value).toBe(false)
    expect(localStorage.getItem('main-layout-drawer-opened')).toBe('false')

    second.open()
    await nextTick()
    expect(first.isOpened.value).toBe(true)
    expect(second.isOpened.value).toBe(true)
    expect(localStorage.getItem('main-layout-drawer-opened')).toBe('true')
  })
})
