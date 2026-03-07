<template>
  <div v-if="item" class="flex flex-col gap-2 flex-1">
    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-1">
        <span class="text-gray-5 flex items-center gap-1 mb-1">SKLADOVÁ POLOŽKA</span>
        <h1 class="text-primary mb-1">
          <a
            @click="
              $router.push({
                name: 'productDetail',
                params: { productCode: item.product.code },
              })
            "
            class="link"
            >{{ item.product.name }}</a
          >
        </h1>
        <span class="flex items-center gap-1 mb-3">
          <small class="text-gray-5">kód produktu:</small>
          <h5>{{ item.product.code }}</h5>
        </span>

        <q-list dense class="mt-2 mb-2">
          <q-item>
            <q-item-section>Typ položky</q-item-section>
            <q-item-section avatar>
              <div class="flex items-center gap-2">
                <span class="text-gray-5">{{ trackingLabel }}</span>
                <PackageTypeBadge :package-type="item.package?.type" />
              </div>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Množství</q-item-section>
            <q-item-section avatar>
              <div class="flex items-center">
                <WarehouseItemAmountBadge :item="item" />
              </div>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Aktuální lokace</q-item-section>
            <q-item-section avatar>
              <a
                @click="
                  $router.push({
                    name: 'warehouses',
                    query: { location: item.location.code },
                  })
                "
                class="link"
                >{{ item.location.code }}</a
              >
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Příjemka</q-item-section>
            <q-item-section avatar>
              <a
                v-if="inboundOrderCode"
                @click="
                  $router.push({
                    name: 'warehouseInboundOrderDetail',
                    params: { code: inboundOrderCode },
                  })
                "
                class="link"
                >{{ inboundOrderCode }}</a
              >
              <span v-else class="text-gray-5">-</span>
            </q-item-section>
          </q-item>
        </q-list>

        <div v-if="item.primary_barcode" class="mt-2">
          <BarcodeElement :barcode="item.primary_barcode" :width="1.6" text-align="left" />
        </div>
      </ForegroundPanel>
    </div>
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> SKLADOVÁ POLOŽKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import { warehouseApiRoutesWarehouseGetWarehouseItem } from '@/client'
import BarcodeElement from '@/components/BarcodeElement.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import PackageTypeBadge from '@/components/PackageTypeBadge.vue'
import WarehouseItemAmountBadge from '@/components/warehouse/WarehouseItemAmountBadge.vue'
import { useApi } from '@/composables/use-api'
import { computed } from 'vue'

const props = defineProps<{ itemId: string }>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesWarehouseGetWarehouseItem({
  path: { item_id: Number(props.itemId) },
})

const data = onResponse(response)
const item = data?.data

const inboundOrderCode =
  (item as { inbound_order_code?: string | null } | undefined)?.inbound_order_code ?? null

const trackingLabel = computed(() => {
  if (!item) {
    return ''
  }
  if (item.tracking_level === 'FUNGIBLE') {
    return 'fungible'
  }
  if (item.tracking_level === 'BATCH') {
    return 'batch'
  }
  return 'serial'
})
</script>
