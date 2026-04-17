<template>
  <div v-if="item" class="flex flex-col gap-2 flex-1">
    <div class="flex justify-between flex-wrap">
      <q-breadcrumbs class="mb-5 flex-[3]">
        <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Produkty" :to="{ name: 'products' }" />
        <q-breadcrumbs-el
          :label="item.product.name"
          :to="{ name: 'productDetail', params: { productCode: item.product.code } }"
        />
        <q-breadcrumbs-el :label="item.primary_barcode ?? `Skladová položka #${item.id}`" />
      </q-breadcrumbs>
      <div class="flex flex-col items-end gap-3 flex-1">
        <q-btn flat color="primary" icon-right="sym_o_query_stats" @click="auditDialog = true">
          <q-tooltip :offset="[0, 10]">Zobrazit historii</q-tooltip>
        </q-btn>
      </div>
    </div>

    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-1">
        <div class="flex justify-between">
          <div>
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
          </div>
          <div v-if="item.batch?.primary_barcode">
            <BarcodeElement
              :barcode="item.batch.primary_barcode.code"
              :width="2"
              :height="40"
              text-align="right"
            />
          </div>
          <div v-else-if="item.primary_barcode">
            <BarcodeElement
              :barcode="item.primary_barcode"
              :width="2"
              :height="40"
              text-align="right"
            />
          </div>
          <span
            v-else
            class="text-gray-5 h-10 font-mono text-xs bg-gray-2 px-5 rounded flex items-center"
          >
            Není evidováno
          </span>
        </div>
        <q-list dense class="mt-2 mb-2" separator>
          <q-item>
            <q-item-section>Typ položky</q-item-section>
            <q-item-section avatar>
              <warehouse-item-type-badge-group :item="item" />
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
          <q-item>
            <q-item-section>Výdejka</q-item-section>
            <q-item-section avatar>
              <a
                v-if="outboundOrderCode"
                @click="
                  $router.push({
                    name: 'warehouseOutboundOrderDetail',
                    params: { code: outboundOrderCode },
                  })
                "
                class="link"
                >{{ outboundOrderCode }}</a
              >
              <span v-else class="text-gray-5">-</span>
            </q-item-section>
          </q-item>
          <q-item v-if="item.batch">
            <q-item-section>Šarže</q-item-section>
            <q-item-section avatar>
              <span>{{ item.batch.primary_barcode?.code ?? `Šarže #${item.batch.id}` }}</span>
            </q-item-section>
          </q-item>
        </q-list>
      </ForegroundPanel>
    </div>

    <RightSideDialog
      v-model:show="auditDialog"
      title="Historie skladové položky"
      panel-class="w-[min(100vw,780px)]"
    >
      <WarehouseItemAuditTimeline :entries="item.audits ?? []" class="p-5" />

      <template #footer>
        <div class="flex justify-end">
          <q-btn flat color="primary" label="Zavřít" @click="auditDialog = false" />
        </div>
      </template>
    </RightSideDialog>
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
import RightSideDialog from '@/components/layout/RightSideDialog.vue'
import WarehouseItemAmountBadge from '@/components/warehouse/WarehouseItemAmountBadge.vue'
import WarehouseItemAuditTimeline from '@/components/warehouse/WarehouseItemAuditTimeline.vue'
import WarehouseItemTypeBadgeGroup from '@/components/warehouse/WarehouseItemTypeBadgeGroup.vue'
import { useApi } from '@/composables/use-api'
import { ref } from 'vue'

const props = defineProps<{ itemId: string }>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesWarehouseGetWarehouseItem({
  path: { item_id: Number(props.itemId) },
})

const data = onResponse(response)
const item = data?.data

const inboundOrderCode = item?.inbound_order_code ?? null

const outboundOrderCode = item?.outbound_order_code ?? null

const auditDialog = ref(false)
</script>
