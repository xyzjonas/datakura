import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OutboundItemRequirements from '../OutboundItemRequirements.vue'
import OutboundOrderItemRequirementsDialog from '../OutboundOrderItemRequirementsDialog.vue'

installQuasarPlugin()

const mountIt = (props: Record<string, unknown> = {}) =>
  mount(OutboundItemRequirements, {
    props: { productName: 'Matice', productCode: 'P1', ...props },
    global: {
      stubs: { OutboundOrderItemRequirementsDialog: true, PackageTypeBadge: true },
    },
  })

describe('OutboundItemRequirements', () => {
  it('opens the requirements dialog from the button', async () => {
    const wrapper = mountIt()
    const dialog = wrapper.findComponent(OutboundOrderItemRequirementsDialog)
    expect(dialog.props('show')).toBe(false)

    await wrapper.get('[data-test="specify-requirements"]').trigger('click')

    expect(dialog.props('show')).toBe(true)
    expect(dialog.props('productCode')).toBe('P1')
  })

  it('is disabled until a product is chosen', () => {
    const wrapper = mountIt({ productCode: '' })
    expect(wrapper.get('[data-test="specify-requirements"]').attributes('disabled')).toBeDefined()
  })

  it.each([
    [{}, true],
    [{ batchCode: 'BAT-1' }, false],
    [{ packageTypeName: 'B0100' }, false],
  ])('"no requirement" hint for %o -> %s', (props, shown) => {
    expect(mountIt(props).text().includes('Bez požadavku')).toBe(shown)
  })

  it('updates both models and then emits save', async () => {
    const updates: Record<string, unknown> = {}
    const wrapper = mountIt({
      'onUpdate:packageTypeName': (v: unknown) => (updates.pkg = v),
      'onUpdate:batchCode': (v: unknown) => (updates.batch = v),
    })

    wrapper.findComponent(OutboundOrderItemRequirementsDialog).vm.$emit('save', {
      desired_package_type_name: null,
      desired_batch_code: 'BAT-9',
    })

    expect(updates).toEqual({ pkg: null, batch: 'BAT-9' })
    expect(wrapper.emitted('save')).toHaveLength(1)
  })

  it('clearing (both null) is propagated as well', () => {
    const wrapper = mountIt({ batchCode: 'BAT-1' })

    wrapper.findComponent(OutboundOrderItemRequirementsDialog).vm.$emit('save', {
      desired_package_type_name: null,
      desired_batch_code: null,
    })

    expect(wrapper.emitted('update:batchCode')?.[0]).toEqual([null])
    expect(wrapper.emitted('save')).toHaveLength(1)
  })
})
