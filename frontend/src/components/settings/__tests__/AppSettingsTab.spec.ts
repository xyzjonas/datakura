import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AppSettingsTab from '@/components/settings/AppSettingsTab.vue'

const mocks = vi.hoisted(() => ({
  setDefaultPrinter: vi.fn(),
  createPrinter: vi.fn(),
  whoami: vi.fn(),
  user: {
    value: {
      username: 'john',
      default_printer: {
        code: 'ZEBRA-01',
        description: 'Front desk printer',
        created: '2026-04-01T10:00:00Z',
        changed: '2026-04-01T10:00:00Z',
      },
    },
  },
  scannerMode: { value: false },
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesAuthSetDefaultPrinter: mocks.setDefaultPrinter,
  warehouseApiRoutesPrintersCreatePrinter: mocks.createPrinter,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown }) => response.data,
  }),
}))

vi.mock('@/composables/use-auth', () => ({
  useAuth: () => ({
    user: mocks.user,
    whoami: mocks.whoami,
  }),
}))

vi.mock('@/composables/use-app-settings', () => ({
  useAppSettings: () => ({
    scannerMode: mocks.scannerMode,
  }),
}))

describe('AppSettingsTab', () => {
  beforeEach(() => {
    mocks.setDefaultPrinter.mockReset()
    mocks.createPrinter.mockReset()
    mocks.whoami.mockReset()
    mocks.user.value = {
      username: 'john',
      default_printer: {
        code: 'ZEBRA-01',
        description: 'Front desk printer',
        created: '2026-04-01T10:00:00Z',
        changed: '2026-04-01T10:00:00Z',
      },
    }
    mocks.scannerMode.value = false
  })

  it('saves selected default printer and refreshes current user', async () => {
    mocks.setDefaultPrinter.mockResolvedValue({ data: { data: { code: 'PACK-01' } } })

    const wrapper = mount(AppSettingsTab, {
      global: {
        stubs: {
          QBtn: {
            props: ['label', 'icon', 'disable', 'loading'],
            emits: ['click'],
            template:
              '<button :data-label="label" :data-icon="icon" :disabled="disable" @click="$emit(\'click\')"><slot />{{ label }}</button>',
          },
          QList: { template: '<div><slot /></div>' },
          QItem: { template: '<div><slot /></div>' },
          QItemSection: { template: '<div><slot /></div>' },
          QItemLabel: { template: '<div><slot /></div>' },
          QToggle: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template:
              '<input type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', !modelValue)" />',
          },
          QBadge: { template: '<span><slot /></span>' },
          QCard: { template: '<div><slot /></div>' },
          PrinterSelect: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template:
              '<button data-test="select-printer" @click="$emit(\'update:modelValue\', \'PACK-01\')">select printer</button>',
          },
          PrinterUpsertDialog: {
            props: ['show', 'modelValue'],
            template: '<div />',
          },
        },
      },
    })

    expect(wrapper.text()).toContain('ZEBRA-01')

    await wrapper.get('[data-test="select-printer"]').trigger('click')
    await wrapper.get('[data-label="uložit výchozí tiskárnu"]').trigger('click')
    await flushPromises()

    expect(mocks.setDefaultPrinter).toHaveBeenCalledWith({
      body: { printer_code: 'PACK-01' },
    })
    expect(mocks.whoami).toHaveBeenCalled()
  })

  it('clears default printer assignment', async () => {
    mocks.setDefaultPrinter.mockResolvedValue({ data: { data: null } })

    const wrapper = mount(AppSettingsTab, {
      global: {
        stubs: {
          QBtn: {
            props: ['label', 'icon', 'disable', 'loading'],
            emits: ['click'],
            template:
              '<button :data-label="label" :data-icon="icon" :disabled="disable" @click="$emit(\'click\')"><slot />{{ label }}</button>',
          },
          QList: { template: '<div><slot /></div>' },
          QItem: { template: '<div><slot /></div>' },
          QItemSection: { template: '<div><slot /></div>' },
          QItemLabel: { template: '<div><slot /></div>' },
          QToggle: { template: '<div />' },
          QBadge: { template: '<span><slot /></span>' },
          QCard: { template: '<div><slot /></div>' },
          PrinterSelect: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<div />',
          },
          PrinterUpsertDialog: {
            props: ['show', 'modelValue'],
            template: '<div />',
          },
        },
      },
    })

    await wrapper.get('[data-label="odebrat přiřazení"]').trigger('click')
    await flushPromises()

    expect(mocks.setDefaultPrinter).toHaveBeenCalledWith({
      body: { printer_code: null },
    })
    expect(mocks.whoami).toHaveBeenCalled()
  })
})
