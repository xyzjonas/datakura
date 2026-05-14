import { installQuasarPlugin } from '@quasar/quasar-app-extension-testing-unit-vitest'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import BarcodeElement from '../BarcodeElement.vue'

const { jsBarcodeMock } = vi.hoisted(() => ({
  jsBarcodeMock: vi.fn(),
}))

vi.mock('jsbarcode', () => ({
  default: jsBarcodeMock,
}))

installQuasarPlugin()

describe('BarcodeElement', () => {
  it('redraws barcode when barcode prop changes', async () => {
    const wrapper = mount(BarcodeElement, {
      props: {
        barcode: '1111111111111',
      },
    })

    expect(jsBarcodeMock).toHaveBeenCalledTimes(1)
    expect(jsBarcodeMock).toHaveBeenLastCalledWith(
      wrapper.find('svg').element,
      '1111111111111',
      expect.objectContaining({
        background: 'white',
        lineColor: 'black',
      }),
    )

    await wrapper.setProps({ barcode: '2222222222222' })

    expect(jsBarcodeMock).toHaveBeenCalledTimes(2)
    expect(jsBarcodeMock).toHaveBeenLastCalledWith(
      wrapper.find('svg').element,
      '2222222222222',
      expect.objectContaining({
        background: 'white',
        lineColor: 'black',
      }),
    )
  })
})
