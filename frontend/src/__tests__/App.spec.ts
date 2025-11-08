import { describe, it, expect } from 'vitest'

import { mount } from '@vue/test-utils'
import App from '../App.vue'
import { createRouter, createWebHistory } from 'vue-router'
import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'

installQuasarPlugin()

// Define some test routes
const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div>You did it!</div>' } }],
})

describe('App', () => {
  it('mounts renders properly', async () => {
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.text()).toContain('You did it!')
  })
})
