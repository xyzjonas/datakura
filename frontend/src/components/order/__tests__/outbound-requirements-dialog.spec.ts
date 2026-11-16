import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CountrySelect from '../../selects/CountrySelect.vue'
import OutboundOrderItemRequirementsDialog from '../OutboundOrderItemRequirementsDialog.vue'

installQuasarPlugin()

const stubs = {
  QDialog: { template: '<div><slot /></div>' },
  QCard: { template: '<div><slot /></div>' },
  QForm: { template: '<form @submit.prevent="$emit(\'submit\')"><slot /></form>' },
  QBtnDropdown: { template: '<div><slot /></div>' },
  PackageTypeSearchSelect: true,
  CertifiedStockPicker: true,
  CountrySelect: true,
}

const mountIt = async (props: Record<string, unknown> = {}) => {
  const wrapper = mount(OutboundOrderItemRequirementsDialog, {
    props: { productName: 'Matice', productCode: 'P1', show: false, ...props },
    global: { stubs },
  })
  await wrapper.setProps({ show: true })
  return wrapper
}

const save = async (wrapper: Awaited<ReturnType<typeof mountIt>>) => {
  await wrapper.get('form').trigger('submit')
  return wrapper.emitted('save')?.at(-1)?.[0]
}

describe('OutboundOrderItemRequirementsDialog', () => {
  it('starts without any requirement, so it is valid out of the box', async () => {
    const wrapper = await mountIt()

    expect(wrapper.find('[data-test="no-requirements"]').exists()).toBe(true)
    expect(wrapper.get('[data-test="save-requirements"]').attributes('disabled')).toBeUndefined()
  })

  it('can require just a country', async () => {
    const wrapper = await mountIt()
    await wrapper.get('[data-test="add-country"]').trigger('click')

    wrapper.findComponent(CountrySelect).vm.$emit('update:modelValue', 'DE')
    await wrapper.vm.$nextTick()

    expect(await save(wrapper)).toEqual({
      desired_package_type_name: null,
      desired_batch_code: null,
      desired_batch_certification: null,
      required_origin_country: 'DE',
    })
  })

  it('combines several requirements', async () => {
    const wrapper = await mountIt({ desiredBatchCode: 'BAT-1', requiredOriginCountry: 'CZ' })

    expect(wrapper.find('[data-test="requirement-batch"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="requirement-country"]').exists()).toBe(true)
    expect(await save(wrapper)).toEqual({
      desired_package_type_name: null,
      desired_batch_code: 'BAT-1',
      desired_batch_certification: null,
      required_origin_country: 'CZ',
    })
  })

  it('restores the existing requirements as rows', async () => {
    const wrapper = await mountIt({
      desiredPackageTypeName: 'B0100',
      desiredBatchCode: 'BAT-1',
      requiredOriginCountry: 'CZ',
    })

    for (const type of ['package', 'batch', 'country']) {
      expect(wrapper.find(`[data-test="requirement-${type}"]`).exists()).toBe(true)
    }
    expect(wrapper.find('[data-test="add-country"]').exists()).toBe(false)
  })

  it('removing a row drops that requirement only', async () => {
    const wrapper = await mountIt({ desiredBatchCode: 'BAT-1', requiredOriginCountry: 'CZ' })

    await wrapper.get('[data-test="remove-country"]').trigger('click')

    expect(await save(wrapper)).toEqual({
      desired_package_type_name: null,
      desired_batch_code: 'BAT-1',
      desired_batch_certification: null,
      required_origin_country: null,
    })
  })

  it('a batch and a certification exclude each other', async () => {
    const wrapper = await mountIt({ desiredBatchCode: 'BAT-1' })
    expect(wrapper.find('[data-test="add-certification"]').exists()).toBe(false)

    await wrapper.get('[data-test="remove-batch"]').trigger('click')
    expect(wrapper.find('[data-test="add-certification"]').exists()).toBe(true)
    await wrapper.get('[data-test="add-certification"]').trigger('click')
    expect(wrapper.find('[data-test="add-batch"]').exists()).toBe(false)
  })

  it('a certification row cannot be saved before one is picked', async () => {
    const wrapper = await mountIt()
    await wrapper.get('[data-test="add-certification"]').trigger('click')

    expect(wrapper.get('[data-test="save-requirements"]').attributes('disabled')).toBeDefined()
  })

  it('"vymazat vše" clears every requirement', async () => {
    const wrapper = await mountIt({
      desiredPackageTypeName: 'B0100',
      requiredOriginCountry: 'CZ',
    })

    const clear = wrapper.findAll('button').find((b) => b.text().includes('vymazat vše'))
    await clear!.trigger('click')

    expect(wrapper.emitted('save')?.at(-1)?.[0]).toEqual({
      desired_package_type_name: null,
      desired_batch_code: null,
      desired_batch_certification: null,
      required_origin_country: null,
    })
  })

  it('opens with the initial mode as the only row when nothing is set', async () => {
    const wrapper = await mountIt({ initialMode: 'batch' })

    expect(wrapper.find('[data-test="requirement-batch"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="no-requirements"]').exists()).toBe(false)
  })

  it('shows the certification of the saved batch and keeps it on save', async () => {
    const cert = { id: 4, code: 'ISO-9001' }
    const wrapper = await mountIt({
      desiredBatchCode: 'BAT-1',
      desiredBatchCertification: cert,
    })

    expect(wrapper.get('[data-test="batch-certification"]').text()).toContain('ISO-9001')
    expect(((await save(wrapper)) as Record<string, unknown>).desired_batch_certification).toEqual({
      code: 'ISO-9001',
    })
  })

  it('hides the certification once the batch code is changed', async () => {
    const wrapper = await mountIt({
      desiredBatchCode: 'BAT-1',
      desiredBatchCertification: { id: 4, code: 'ISO-9001' },
    })

    await wrapper.get('[data-test="requirement-batch"] input').setValue('BAT-2')

    expect(wrapper.find('[data-test="batch-certification"]').exists()).toBe(false)
  })
})
