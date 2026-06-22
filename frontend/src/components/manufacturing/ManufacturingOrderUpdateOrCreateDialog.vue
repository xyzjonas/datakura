<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-start items-center mb-3 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>
        <q-form class="flex flex-col gap-2" @submit="submit">
          <q-input
            v-model.trim="item.description"
            outlined
            label="Popis"
            hint="Popis výrobního příkazu (volitelné)"
            autogrow
          />
          <q-input
            v-model.trim="item.note"
            outlined
            label="Poznámka"
            hint="Interní poznámka (volitelné)"
            type="textarea"
          />
          <CustomerSearchSelect
            v-model="supplier"
            label="Dodavatel / výrobce"
            hint="Zákazník zajišťující výrobu (volitelné)"
            :required="false"
          />
          <q-toggle v-model="item.is_external" label="Externí výroba" />
          <CustomerSearchSelect
            v-if="item.is_external"
            v-model="customer"
            label="Pracoviště (zákazník)"
            hint="Výrobní pracoviště"
            :required="false"
          />
          <q-btn
            type="submit"
            unelevated
            color="primary"
            :label="submitLabel"
            class="h-[3rem] mt-3"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type {
  CustomerBaseSchema,
  ManufacturingOrderCreateOrUpdateSchema,
  ManufacturingOrderSchema,
} from '@/client'
import CustomerSearchSelect from '@/components/selects/CustomerSearchSelect.vue'
import { ref, watch } from 'vue'

type Props = {
  title?: string
  submitLabel?: string
  orderIn?: ManufacturingOrderSchema
}

const showDialog = defineModel('show', { default: false })
const props = withDefaults(defineProps<Props>(), {
  title: 'Nový výrobní příkaz',
  submitLabel: 'vytvořit',
})

const customer = ref<CustomerBaseSchema | undefined>(props.orderIn?.customer ?? undefined)
const supplier = ref<CustomerBaseSchema | undefined>(props.orderIn?.supplier ?? undefined)

const propToRef = (order?: ManufacturingOrderSchema): ManufacturingOrderCreateOrUpdateSchema => {
  if (!order) {
    return {
      description: '',
      note: '',
      is_external: false,
      customer_code: null,
      customer_name: null,
      supplier_code: null,
      supplier_name: null,
    }
  }
  return {
    description: order.description ?? '',
    note: order.note ?? '',
    is_external: order.is_external,
    customer_code: order.customer?.code ?? null,
    customer_name: order.customer?.name ?? null,
    supplier_code: order.supplier?.code ?? null,
    supplier_name: order.supplier?.name ?? null,
  }
}

const item = ref<ManufacturingOrderCreateOrUpdateSchema>(propToRef(props.orderIn))

watch(customer, (val) => {
  if (val) {
    item.value.customer_code = val.code
    item.value.customer_name = val.name
  } else {
    item.value.customer_code = null
    item.value.customer_name = null
  }
})

watch(supplier, (val) => {
  if (val) {
    item.value.supplier_code = val.code
    item.value.supplier_name = val.name
  } else {
    item.value.supplier_code = null
    item.value.supplier_name = null
  }
})

watch(
  () => item.value.is_external,
  (val) => {
    if (!val) {
      item.value.customer_code = null
      item.value.customer_name = null
      customer.value = undefined
    }
  },
)

const emit = defineEmits<{
  (e: 'createOrder', item: ManufacturingOrderCreateOrUpdateSchema): void
}>()

const submit = () => {
  emit('createOrder', item.value)
}

const reset = () => {
  item.value = {
    description: '',
    note: '',
    is_external: false,
    customer_code: null,
    customer_name: null,
    supplier_code: null,
    supplier_name: null,
  }
  customer.value = undefined
  supplier.value = undefined
  showDialog.value = false
}

defineExpose({ reset })
</script>
