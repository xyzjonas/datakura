<template>
  <div v-if="order" class="w-full flex flex-col gap-2">
    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[400px] flex-1">
        <span class="text-gray-5 flex items-center gap-1">OBJEDNÁVKA</span>
        <h1 class="text-primary mb-1">{{ order.code }}</h1>
        <span class="flex items-center gap-1 mb-3">
          <small class="text-gray-5">kód:</small>
          <h5>{{ order.code }}</h5>
          <q-btn flat round size="8px" icon="content_copy"></q-btn>
        </span>

        <q-list dense class="mt-2" separator>
          <q-item>
            <q-item-section>Číslo dokladu</q-item-section>
            <q-item-section avatar>
              <span class="flex gap-1">
                {{ order.code }}
                <q-btn flat round size="8px" icon="content_copy"></q-btn>
              </span>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Externí číslo</q-item-section>
            <q-item-section avatar>
              <span class="flex gap-1">
                {{ order.external_code }}
                <q-btn flat round size="8px" icon="content_copy"></q-btn>
              </span>
            </q-item-section>
          </q-item>
        </q-list>
        <div class="mt-auto flex flex-row-reverse">
          <q-btn outline color="primary" icon="edit" label="upravit" disable></q-btn>
        </div>
      </ForegroundPanel>
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-[2]">
        <q-list dense separator>
          <q-item>
            <q-item-section>Požadovaný termín dodání</q-item-section>
            <q-item-section avatar>{{
              new Date(order.created).toLocaleDateString()
            }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Datum zrušení</q-item-section>
            <q-item-section avatar>{{
              new Date(order.created).toLocaleDateString()
            }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Zboží přijato</q-item-section>
            <q-item-section avatar>{{
              new Date(order.created).toLocaleDateString()
            }}</q-item-section>
          </q-item>
        </q-list>
        <q-list dense class="mt-auto">
          <q-item>
            <q-item-section>
              <span class="text-xs text-gray-5">Číslo příjemky</span>
              <span>N/A</span>
            </q-item-section>
            <q-item-section avatar
              ><q-btn disable label="naskladnit" outline color="primary" icon="sym_o_input"
            /></q-item-section>
          </q-item>
        </q-list>
      </ForegroundPanel>
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-1">
        <span class="text-gray-5 flex items-center gap-1">DODAVATEL</span>
        <h1 class="text-primary mb-1">{{ order.supplier.name }}</h1>
        <span class="flex items-center gap-1 mb-3">
          <small class="text-gray-5">kód:</small>
          <h5>{{ order.supplier.code }}</h5>
          <q-btn flat round size="8px" icon="content_copy"></q-btn>
        </span>
        <q-list dense separator>
          <q-item>
            <q-item-section>IČO</q-item-section>
            <q-item-section avatar>{{ order.supplier.identification }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>DIČ</q-item-section>
            <q-item-section avatar>{{ order.supplier.tax_identification }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Kontakt</q-item-section>
            <q-item-section avatar>{{ contact?.email }}</q-item-section>
          </q-item>
        </q-list>
      </ForegroundPanel>
    </div>
    <div class="flex items-center gap-2 mt-5">
      <h2>Položky objednávky</h2>
      <q-btn unelevated color="primary" flat dense icon="sym_o_splitscreen_add"></q-btn>
      <TotalWeight :order="order" class="ml-auto mr-5" />
      <TotalPrice :order="order" />
    </div>
    <div>
      <ProductsList v-model:items="order.items" :currency="order.currency" />
    </div>
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> OBJEDNÁVKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import { warehouseApiRoutesOrdersGetIncomingOrder, type IncomingOrderSchema } from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import ProductsList from '@/components/order/ProductsList.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import TotalWeight from '@/components/order/TotalWeight.vue'
import { computed, ref } from 'vue'

const props = defineProps<{ code: string }>()
const order = ref<IncomingOrderSchema>()

const response = await warehouseApiRoutesOrdersGetIncomingOrder({
  path: { order_code: props.code },
})
order.value = response.data

const contact = computed(() => {
  if (!order.value?.supplier.contacts) {
    return undefined
  }
  if (order.value.supplier.contacts.length <= 0) {
    return undefined
  }
  return order.value.supplier.contacts[0]
})
</script>

<style lang="scss" scoped></style>
