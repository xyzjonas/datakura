import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PrintersTable from '@/components/settings/printers/PrintersTable.vue'

const mocks = vi.hoisted(() => ({
  getPrinters: vi.fn(),
  createPrinter: vi.fn(),
  updatePrinter: vi.fn(),
  deletePrinter: vi.fn(),
  whoami: vi.fn(),
  user: {
    value: {
      default_printer: {
        code: 'ZEBRA-01',
      },
    },
  },
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesPrintersGetPrinters: mocks.getPrinters,
  warehouseApiRoutesPrintersCreatePrinter: mocks.createPrinter,
  warehouseApiRoutesPrintersUpdatePrinter: mocks.updatePrinter,
  warehouseApiRoutesPrintersDeletePrinter: mocks.deletePrinter,
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

describe('PrintersTable', () => {
  beforeEach(() => {
    mocks.getPrinters.mockReset()
    mocks.createPrinter.mockReset()
    mocks.updatePrinter.mockReset()
    mocks.deletePrinter.mockReset()
    mocks.whoami.mockReset()
    mocks.user.value = {
      default_printer: {
        code: 'ZEBRA-01',
      },
    }
    mocks.getPrinters.mockResolvedValue({
      data: {
        data: [
          {
            code: 'ZEBRA-01',
            description: 'Front desk printer',
            created: '2026-04-01T10:00:00Z',
            changed: '2026-04-01T10:00:00Z',
          },
        ],
      },
    })
  })

  it('loads printers and refreshes current user after deleting assigned printer', async () => {
    mocks.deletePrinter.mockResolvedValue({
      data: {
        data: {
          code: 'ZEBRA-01',
        },
      },
    })

    const wrapper = mount(PrintersTable, {
      global: {
        stubs: {
          QTable: {
            props: ['rows'],
            template: `
              <div>
                <slot name="top-left" />
                <slot name="top-right" />
                <div v-for="row in rows" :key="row.code">
                  <slot name="body-cell-code" :row="row" />
                  <slot name="body-cell-description" :row="row" />
                  <slot name="body-cell-actions" :row="row" />
                </div>
              </div>
            `,
          },
          QTd: { template: '<div><slot /></div>' },
          QBtn: {
            props: ['label', 'icon'],
            emits: ['click'],
            template:
              '<button :data-label="label" :data-icon="icon" @click="$emit(\'click\')"><slot />{{ label }}</button>',
          },
          QTooltip: { template: '<div><slot /></div>' },
          SearchInput: {
            props: ['modelValue'],
            emits: ['update:modelValue'],
            template: '<div />',
          },
          PrinterUpsertDialog: {
            props: ['show', 'modelValue'],
            template: '<div />',
          },
          ConfirmDialog: {
            props: ['show', 'title'],
            emits: ['confirm', 'update:show'],
            template:
              '<div v-if="show"><slot /><button data-test="confirm-delete" @click="$emit(\'confirm\')">confirm</button></div>',
          },
        },
      },
    })

    await flushPromises()

    expect(wrapper.text()).toContain('ZEBRA-01')

    await wrapper.get('[data-icon="delete"]').trigger('click')
    await wrapper.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()

    expect(mocks.deletePrinter).toHaveBeenCalledWith({
      path: { printer_code: 'ZEBRA-01' },
    })
    expect(mocks.whoami).toHaveBeenCalled()
  })
})
