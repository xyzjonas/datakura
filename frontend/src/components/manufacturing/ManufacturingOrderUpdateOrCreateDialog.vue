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
            label="Dodavatel"
            hint="Zákazník zajišťující výrobu (volitelné)"
            :required="false"
          />
          <q-toggle v-model="item.is_external" label="Externí výroba" />
          <CustomerSearchSelect
            v-show="item.is_external"
            v-model="customer"
            label="Zákazník"
            hint="Zákazník objednávající výrobu (volitelné)"
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
import { warehouseApiRoutesCustomerGetCustomers } from '@/client'
import CustomerSearchSelect from '@/components/selects/CustomerSearchSelect.vue'
import { onMounted, ref, watch } from 'vue'

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

const selfCustomer = ref<CustomerBaseSchema | undefined>()

onMounted(async () => {
  const result = await warehouseApiRoutesCustomerGetCustomers({
    query: { is_self: true, page: 1, page_size: 1 },
  })
  const self = result.data?.data[0]
  if (!self) return
  selfCustomer.value = self
  if (!props.orderIn) {
    supplier.value = self
    customer.value = self
    item.value.supplier_code = self.code
    item.value.supplier_name = self.name
    item.value.customer_code = self.code
    item.value.customer_name = self.name
  }
})

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
    customer_code: selfCustomer.value?.code ?? null,
    customer_name: selfCustomer.value?.name ?? null,
    supplier_code: selfCustomer.value?.code ?? null,
    supplier_name: selfCustomer.value?.name ?? null,
  }
  customer.value = selfCustomer.value
  supplier.value = selfCustomer.value
  showDialog.value = false
}

defineExpose({ reset })
</script>
