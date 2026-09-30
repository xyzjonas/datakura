import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref, type Ref } from 'vue'

import DataImportSettingsTab from '@/components/settings/DataImportSettingsTab.vue'

const mocks = vi.hoisted(() => ({
  start: vi.fn(),
  stopWatching: vi.fn(),
  status: null as unknown as Ref<unknown>,
  running: null as unknown as Ref<boolean>,
}))

vi.mock('@/composables/use-data-import-job', () => ({
  useDataImportJob: () => ({
    start: mocks.start,
    stopWatching: mocks.stopWatching,
    status: mocks.status,
    running: mocks.running,
  }),
}))

const RESULT = {
  products: { created: 3, updated: 1, skipped: 0, barcodes_attached: 4, warnings: ['P warn'] },
  customers: { created: 2, updated: 0, contacts: 5, groups_created: 1, warnings: ['C warn'] },
  warehouses: [
    {
      warehouse: 'Centrála',
      warehouse_created: true,
      locations_created: 2,
      locations_existing: 0,
      items_created: 7,
    },
  ],
}

const file = (name: string) => new File(['[]'], name, { type: 'application/json' })

const stubs = {
  QBtn: {
    props: ['label', 'disable', 'loading', 'icon'],
    emits: ['click'],
    template:
      '<button :data-label="label" :data-icon="icon" :disabled="disable" :data-loading="loading" @click="$emit(\'click\')">{{ label }}<slot /></button>',
  },
  QExpansionItem: { template: '<div><slot /></div>' },
  QCard: { template: '<div><slot /></div>' },
  QBadge: { template: '<span><slot /></span>' },
  QBanner: { template: '<div><slot /></div>' },
  QTooltip: true,
  QInput: {
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template:
      '<input data-test="warehouse-name" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  DataImportProgress: {
    props: ['status'],
    emits: ['stop'],
    template: '<div data-test="progress" />',
  },
  DataImportResult: {
    props: ['result'],
    template: '<div data-test="result" />',
  },
  JsonFileInput: {
    props: ['modelValue', 'label'],
    emits: ['update:modelValue'],
    template: '<div :data-label="label" />',
  },
}

const mountTab = () => mount(DataImportSettingsTab, { global: { stubs } })

const submitButton = (wrapper: ReturnType<typeof mountTab>) =>
  wrapper.find('button[data-label="importovat"]')

describe('DataImportSettingsTab', () => {
  beforeEach(() => {
    mocks.start.mockReset()
    mocks.start.mockResolvedValue(true)
    mocks.stopWatching.mockReset()
    mocks.status = ref(null)
    mocks.running = ref(false)
  })

  it('disables import until something is selected', async () => {
    const wrapper = mountTab()
    expect(submitButton(wrapper).attributes('disabled')).toBeDefined()

    const inputs = wrapper.findAllComponents(stubs.JsonFileInput)
    await inputs[0]!.vm.$emit('update:modelValue', file('products.json'))

    expect(submitButton(wrapper).attributes('disabled')).toBeUndefined()
  })

  it('adds and removes warehouse rows and blocks import on incomplete row', async () => {
    const wrapper = mountTab()

    await wrapper.find('button[data-label="přidat sklad"]').trigger('click')
    expect(wrapper.findAll('[data-test="warehouse-name"]')).toHaveLength(1)

    await wrapper.find('[data-test="warehouse-name"]').setValue('Centrála')
    expect(wrapper.text()).toContain('Každý řádek skladu musí mít vyplněný název i soubor.')
    expect(submitButton(wrapper).attributes('disabled')).toBeDefined()

    await wrapper.find('button[data-icon="delete"]').trigger('click')
    expect(wrapper.findAll('[data-test="warehouse-name"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('Žádný sklad nebyl přidán.')
  })

  it('starts the import with the selected files', async () => {
    const wrapper = mountTab()
    const products = file('products.json')
    const fileInputs = wrapper.findAllComponents(stubs.JsonFileInput)
    await fileInputs[0]!.vm.$emit('update:modelValue', products)

    await submitButton(wrapper).trigger('click')

    expect(mocks.start).toHaveBeenCalledTimes(1)
    const body = mocks.start.mock.calls[0]![0]
    expect(body.products_file).toBe(products)
    expect(body.customers_file).toBeUndefined()
    expect(body.warehouse_ids).toEqual([])
  })

  it('locks the form while the import runs', async () => {
    mocks.running.value = true
    const wrapper = mountTab()
    await wrapper.findAllComponents(stubs.JsonFileInput)[0]!.vm.$emit(
      'update:modelValue',
      file('products.json'),
    )

    expect(submitButton(wrapper).attributes('disabled')).toBeDefined()
    expect(submitButton(wrapper).attributes('data-loading')).toBe('true')
  })

  it('renders progress while running and forwards stop-watching', async () => {
    mocks.status.value = { job_id: 'j', state: 'pending' }
    const wrapper = mountTab()

    const progress = wrapper.findComponent(stubs.DataImportProgress)
    expect(progress.exists()).toBe(true)
    expect(wrapper.findComponent(stubs.DataImportResult).exists()).toBe(false)

    await progress.vm.$emit('stop')
    expect(mocks.stopWatching).toHaveBeenCalledTimes(1)
  })

  it('renders the result only after the job succeeded', () => {
    mocks.status.value = { job_id: 'j', state: 'succeeded', percent: 100, result: RESULT }
    const wrapper = mountTab()

    expect(wrapper.findComponent(stubs.DataImportResult).exists()).toBe(true)
    expect(wrapper.findComponent(stubs.DataImportProgress).exists()).toBe(false)
  })

  it('renders progress (with the error) for a failed job and no result', () => {
    mocks.status.value = { job_id: 'j', state: 'failed', error: 'boom' }
    const wrapper = mountTab()

    expect(wrapper.findComponent(stubs.DataImportProgress).exists()).toBe(true)
    expect(wrapper.findComponent(stubs.DataImportResult).exists()).toBe(false)
  })
})
