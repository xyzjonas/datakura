import { beforeEach, describe, expect, it } from 'vitest'

import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import App from '../App.vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import {
  APP_VERSION,
  getInitialLastAcknowledgedVersion,
  lastAcknowledgedVersion,
} from '../utils/version'

installQuasarPlugin()

// Define some test routes
const createTestRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div>You did it!</div>' } }],
  })

const quasarStubs = {
  MainLayout: { template: '<div><slot /></div>' },
  QDialog: {
    props: ['modelValue'],
    template: '<div v-if="modelValue" data-test="whats-new-dialog"><slot /></div>',
  },
  QCard: { template: '<div><slot /></div>' },
  QCardSection: { template: '<section><slot /></section>' },
  QCardActions: { template: '<div><slot /></div>' },
  QBtn: {
    props: ['label'],
    emits: ['click'],
    template: '<button type="button" @click="$emit(\'click\')">{{ label }}</button>',
  },
}

describe('App', () => {
  beforeEach(() => {
    localStorage.clear()
    lastAcknowledgedVersion.value = getInitialLastAcknowledgedVersion()
  })

  it('mounts renders properly', async () => {
    const router = createTestRouter()
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: quasarStubs,
      },
    })

    expect(wrapper.text()).toContain('You did it!')
  })

  it('shows whats new dialog until current version is acknowledged', async () => {
    const router = createTestRouter()
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: quasarStubs,
      },
    })

    await nextTick()

    expect(wrapper.get('[data-test="whats-new-dialog"]').text()).toContain('Co je nového?')
    expect(wrapper.text()).toContain(APP_VERSION)

    await wrapper.get('button').trigger('click')
    await nextTick()

    expect(wrapper.find('[data-test="whats-new-dialog"]').exists()).toBe(false)
  })

  it('does not show dialog when current version is already acknowledged', async () => {
    lastAcknowledgedVersion.value = APP_VERSION

    const router = createTestRouter()
    router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [router],
        stubs: quasarStubs,
      },
    })

    await nextTick()

    expect(wrapper.find('[data-test="whats-new-dialog"]').exists()).toBe(false)
  })
})
