<template>
  <div class="flex">
    <svg :id="barcode" ref="barcodeElement" class="bg-amber"></svg>
  </div>
</template>

<script setup lang="ts">
import JsBarcode from 'jsbarcode'
import { onMounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    barcode: string
    fontSize?: number
    width?: number
    displayValue?: boolean
    textAlign?: 'left' | 'center' | 'right'
  }>(),
  {
    fontSize: 12,
    width: 1,
    displayValue: true,
    textAlign: 'center',
  },
)
const barcodeElement = ref<SVGElement>()

onMounted(() => {
  if (barcodeElement.value) {
    JsBarcode(barcodeElement.value, props.barcode, {
      // background: 'red',
      fontSize: props.fontSize,
      margin: 0,
      ean128: false,
      marginBottom: 0,
      flat: true,
      height: 20,
      width: props.width,
      marginTop: 0,
      textPosition: 'bottom',
      displayValue: props.displayValue,
      textAlign: props.textAlign,
    })
  }
})
</script>

<style lang="scss" scoped></style>
