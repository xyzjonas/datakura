<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>
        <q-form class="flex flex-col gap-3" @submit="submit">
          <div class="text-sm text-muted uppercase font-bold">Vstup (co jde na pracoviště)</div>
          <ProductSearchSelect v-model="inProduct" />
          <ProductAvailability v-if="inProduct" :product-code="inProduct.code" />
          <q-input
            v-model.number="item.in_amount"
            outlined
            label="Počet (vstup)"
            hint="Množství vstupního produktu"
            inputmode="numeric"
            :rules="[rules.atLeastOne]"
          >
            <template #append>
              <span class="text-sm">{{ inProductUom }}</span>
            </template>
          </q-input>

          <q-separator />

          <div class="text-sm text-muted uppercase font-bold">Výstup (co se vrátí z pracoviště)</div>
          <ProductSearchSelect v-model="outProduct" />
          <ProductAvailability v-if="outProduct" :product-code="outProduct.code" />
          <q-input
            v-model.number="item.out_amount"
            outlined
            label="Počet (výstup)"
            hint="Množství výstupního produktu"
            inputmode="numeric"
            :rules="[rules.atLeastOne]"
          >
            <template #append>
              <span class="text-sm">{{ outProductUom }}</span>
            </template>
          </q-input>

          <q-btn type="submit" unelevated color="primary" label="uložit" class="h-[3rem] mt-3" />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { ManufacturingOrderItemCreateSchema, ManufacturingOrderItemSchema, ProductSchema } from '@/client'
import ProductAvailability from '@/components/product/ProductAvailability.vue'
import ProductSearchSelect from '@/components/selects/ProductSearchSelect.vue'
import { rules } from '@/utils/rules'
import { ref, watch } from 'vue'

type Props = {
  title?: string
  itemIn?: ManufacturingOrderItemSchema
}

const showDialog = defineModel('show', { default: false })
const props = withDefaults(defineProps<Props>(), {
  title: 'Přidat položku',
})

const inProductUom = ref('')
const outProductUom = ref('')

const inProduct = ref<ProductSchema | undefined>(
  props.itemIn ? (props.itemIn.in_product as ProductSchema) : undefined,
)
const outProduct = ref<ProductSchema | undefined>(
  props.itemIn ? (props.itemIn.out_product as ProductSchema) : undefined,
)

const item = ref<ManufacturingOrderItemCreateSchema>({
  in_product_code: props.itemIn?.in_product.code ?? '',
  in_product_name: props.itemIn?.in_product.name ?? '',
  in_amount: props.itemIn?.in_amount ?? 0,
  out_product_code: props.itemIn?.out_product.code ?? '',
  out_product_name: props.itemIn?.out_product.name ?? '',
  out_amount: props.itemIn?.out_amount ?? 0,
})

watch(inProduct, (val) => {
  if (val) {
    item.value.in_product_code = val.code
    item.value.in_product_name = val.name
    inProductUom.value = val.unit ?? ''
  } else {
    item.value.in_product_code = ''
    item.value.in_product_name = ''
  }
})

watch(outProduct, (val) => {
  if (val) {
    item.value.out_product_code = val.code
    item.value.out_product_name = val.name
    outProductUom.value = val.unit ?? ''
  } else {
    item.value.out_product_code = ''
    item.value.out_product_name = ''
  }
})

const emit = defineEmits<{
  (e: 'addItem', item: ManufacturingOrderItemCreateSchema): void
}>()

const submit = () => {
  emit('addItem', item.value)
}

const reset = () => {
  item.value = {
    in_product_code: '',
    in_product_name: '',
    in_amount: 0,
    out_product_code: '',
    out_product_name: '',
    out_amount: 0,
  }
  inProduct.value = undefined
  outProduct.value = undefined
  showDialog.value = false
}

defineExpose({ reset })
</script>
