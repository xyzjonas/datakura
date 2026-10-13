import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import UserAvatar from '@/components/user/UserAvatar.vue'

describe('UserAvatar', () => {
  it('shows the image when url is set', () => {
    const wrapper = mount(UserAvatar, { props: { username: 'jonas', url: '/media/a.webp' } })

    expect(wrapper.get('img').attributes('src')).toBe('/media/a.webp')
    expect(wrapper.find('[data-test="avatar-initial"]').exists()).toBe(false)
  })

  it.each([
    ['jonas', 'j'],
    ['  anna', 'a'],
    ['', ''],
  ])('falls back to the first letter of "%s"', (username, initial) => {
    const wrapper = mount(UserAvatar, { props: { username, url: null } })

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.get('[data-test="avatar-initial"]').text()).toBe(initial)
  })
})
