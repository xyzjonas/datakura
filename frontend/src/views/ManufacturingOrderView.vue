<template>
  <div v-if="order" class="w-full flex flex-col gap-5">
    <div class="flex justify-between">
      <q-breadcrumbs class="mb-5">
        <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Výrobní příkazy" :to="{ name: 'manufacturingOrders' }" />
        <q-breadcrumbs-el :label="order.code" />
      </q-breadcrumbs>
      <q-btn flat dense color="primary" icon="sym_o_query_stats" @click="auditDialog = true">
        <q-tooltip :offset="[0, 10]">Zobrazit historii</q-tooltip>
      </q-btn>
    </div>

    <div class="mb-2 flex justify-between items-start md:items-center flex-col md:flex-row gap-5">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">POŽADAVEK VÝROBY</span>
          <h1 class="h1 mb-1">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
        </div>
        <ManufacturingOrderStateBadge :state="order.state" />
      </div>
      <div class="flex gap-2 items-center">
        <q-btn
          v-if="isManufacturingOrderEditable(order)"
          unelevated
          color="primary"
          icon="edit"
          label="upravit"
          @click="editOrderDialog = true"
        />
        <q-btn
          v-if="order.state !== 'cancelled' && order.state !== 'completed'"
          unelevated
          color="negative"
          label="Zrušit"
          icon="sym_o_scan_delete"
          @click="cancelDialog = true"
        />
        <q-btn
          v-if="order.state === 'draft'"
          unelevated
          color="positive"
          icon="sym_o_order_approve"
          label="potvrdit"
          @click="confirmDialog = true"
          :disable="(order.items?.length ?? 0) === 0"
        />
        <q-btn
          v-if="order.state === 'in_progress'"
          unelevated
          color="positive"
          icon="sym_o_check_circle"
          label="Dokončit"
          @click="completeDialog = true"
        />
      </div>
    </div>

    <div class="flex gap-5 flex-col md:flex-row">
      <ManufacturingOrderDetailsListCard :order="order" class="flex-1" />

      <LinkedEntitiesCard
        show-inbound-warehouse-orders
        show-outbound-warehouse-orders
        :inboundWarehouseOrders="order.inbound_warehouse_orders"
        :outboundWarehouseOrders="order.outbound_warehouse_orders"
        :manufacturingOrder="order"
        class="flex-1"
      />
    </div>

    <CommentCard v-if="order.note">{{ order.note }}</CommentCard>

    <ForegroundPanel v-if="$q.screen.gt.md">
      <ManufacturingOrderTimeline :state="order.state" />
    </ForegroundPanel>

    <div class="flex items-center gap-2 mt-5">
      <h2>Položky výrobního příkazu</h2>
      <q-btn
        v-if="isManufacturingOrderEditable(order)"
        flat
        color="primary"
        icon="sym_o_add"
        label="přidat položku"
        @click="addItemDialog = true"
        class="ml-5"
      />
    </div>

    <ForegroundPanel>
      <q-table
        :rows="order.items ?? []"
        :columns="itemColumns"
        row-key="id"
        flat
        hide-bottom
        :pagination="{ rowsPerPage: 0 }"
      >
        <template #body-cell-actions="slotProps">
          <q-td :props="slotProps">
            <div v-if="isManufacturingOrderEditable(order)" class="flex gap-1">
              <q-btn
                flat
                dense
                round
                icon="edit"
                color="primary"
                @click.stop="openEditItem(slotProps.row)"
              />
              <q-btn
                flat
                dense
                round
                icon="delete"
                color="negative"
                @click.stop="removeItem(slotProps.row.id)"
              />
            </div>
          </q-td>
        </template>
        <template #no-data>
          <div class="text-center text-gray-5 py-8 w-full">Žádné položky</div>
        </template>
      </q-table>
    </ForegroundPanel>

    <ManufacturingOrderItemDialog
      ref="addItemDialogComponent"
      v-model:show="addItemDialog"
      title="Přidat položku"
      @add-item="addItem"
    />
    <ManufacturingOrderItemDialog
      v-if="editingItem"
      v-model:show="editItemDialog"
      title="Upravit položku"
      :item-in="editingItem"
      @add-item="updateItem"
    />
    <ManufacturingOrderUpdateOrCreateDialog
      v-model:show="editOrderDialog"
      :order-in="order"
      submit-label="uložit"
      title="Upravit výrobní příkaz"
      @create-order="updateOrder"
    />
    <ConfirmDialog v-model="confirmDialog" title="Potvrdit výrobní příkaz?" @confirm="confirm">
      <span>
        Příkaz přejde do stavu
        <ManufacturingOrderStateBadge state="confirmed" />
        a bude vytvořena výdejka pro odeslání zboží na pracoviště.
      </span>
    </ConfirmDialog>
    <ConfirmDialog v-model="startDialog" title="Spustit výrobu?" @confirm="startProduction">
      <span>
        Příkaz přejde do stavu
        <ManufacturingOrderStateBadge state="in_progress" />
        a bude vytvořena příjemka pro příjem hotových produktů.
      </span>
    </ConfirmDialog>
    <ConfirmDialog v-model="completeDialog" title="Dokončit výrobní příkaz?" @confirm="complete">
      <span>
        Příkaz přejde do stavu
        <ManufacturingOrderStateBadge state="completed" />
        a bude archivován.
      </span>
    </ConfirmDialog>
    <ConfirmDialog v-model:show="cancelDialog" title="Zrušit výrobní příkaz?" @confirm="cancel">
      <span>
        Příkaz bude označen jako
        <ManufacturingOrderStateBadge state="cancelled" />
        a bude archivován.
      </span>
    </ConfirmDialog>
    <AuditLogDialog
      v-model:show="auditDialog"
      source="manufacturing-order"
      :code="order.code"
      title="Historie změn výrobního příkazu"
    />
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5">VÝROBNÍ PŘÍKAZ NENALEZEN</span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesManufacturingOrdersAddItemToManufacturingOrder,
  warehouseApiRoutesManufacturingOrdersGetManufacturingOrder,
  warehouseApiRoutesManufacturingOrdersRemoveItemFromManufacturingOrder,
  warehouseApiRoutesManufacturingOrdersTransitionManufacturingOrder,
  warehouseApiRoutesManufacturingOrdersUpdateItemInManufacturingOrder,
  warehouseApiRoutesManufacturingOrdersUpdateManufacturingOrder,
  type ManufacturingOrderCreateOrUpdateSchema,
  type ManufacturingOrderItemCreateSchema,
  type ManufacturingOrderItemSchema,
  type ManufacturingOrderSchema,
} from '@/client'
import CommentCard from '@/components/CommentCard.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import ManufacturingOrderDetailsListCard from '@/components/manufacturing/ManufacturingOrderDetailsListCard.vue'
import ManufacturingOrderItemDialog from '@/components/manufacturing/ManufacturingOrderItemDialog.vue'
import ManufacturingOrderStateBadge from '@/components/manufacturing/ManufacturingOrderStateBadge.vue'
import ManufacturingOrderTimeline from '@/components/manufacturing/ManufacturingOrderTimeline.vue'
import ManufacturingOrderUpdateOrCreateDialog from '@/components/manufacturing/ManufacturingOrderUpdateOrCreateDialog.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import { useApi } from '@/composables/use-api'
import { isManufacturingOrderEditable } from '@/constants/manufacturing-order'
import type { QTableColumn } from 'quasar'
import { useQuasar } from 'quasar'
import { ref } from 'vue'

const props = defineProps<{ code: string }>()
const order = ref<ManufacturingOrderSchema>()

const { onResponse } = useApi()
const $q = useQuasar()

const response = await warehouseApiRoutesManufacturingOrdersGetManufacturingOrder({
  path: { order_code: props.code },
})
const data = onResponse(response)
if (data) {
  order.value = data.data
}

const itemColumns: QTableColumn[] = [
  {
    name: 'in_product',
    field: (row: ManufacturingOrderItemSchema) => row.in_product.name,
    label: 'Vstupní produkt',
    align: 'left',
  },
  {
    name: 'in_amount',
    field: 'in_amount',
    label: 'Množství (vstup)',
    align: 'left',
    format: (val: number) => String(val),
  },
  {
    name: 'out_product',
    field: (row: ManufacturingOrderItemSchema) => row.out_product.name,
    label: 'Výstupní produkt',
    align: 'left',
  },
  {
    name: 'out_amount',
    field: 'out_amount',
    label: 'Množství (výstup)',
    align: 'left',
    format: (val: number) => String(val),
  },
  { name: 'actions', field: 'id', label: '', align: 'right' },
]

const addItemDialog = ref(false)
const addItemDialogComponent = ref<InstanceType<typeof ManufacturingOrderItemDialog>>()
const auditDialog = ref(false)

const addItem = async (item: ManufacturingOrderItemCreateSchema) => {
  if (!order.value) return
  const res = await warehouseApiRoutesManufacturingOrdersAddItemToManufacturingOrder({
    path: { order_code: order.value.code },
    body: item,
  })
  const itemData = onResponse(res)
  if (itemData) {
    order.value.items = [...(order.value.items ?? []), itemData.data]
    addItemDialogComponent.value?.reset()
  }
}

const editItemDialog = ref(false)
const editingItem = ref<ManufacturingOrderItemSchema>()

const openEditItem = (item: ManufacturingOrderItemSchema) => {
  editingItem.value = item
  editItemDialog.value = true
}

const updateItem = async (item: ManufacturingOrderItemCreateSchema) => {
  if (!order.value || !editingItem.value) return
  const res = await warehouseApiRoutesManufacturingOrdersUpdateItemInManufacturingOrder({
    path: { order_code: order.value.code, item_id: editingItem.value.id },
    body: item,
  })
  const itemData = onResponse(res)
  if (itemData) {
    order.value.items = order.value.items?.map((it) =>
      it.id === editingItem.value!.id ? itemData.data : it,
    )
    editItemDialog.value = false
    editingItem.value = undefined
  }
}

const removeItem = async (itemId: number) => {
  if (!order.value) return
  const res = await warehouseApiRoutesManufacturingOrdersRemoveItemFromManufacturingOrder({
    path: { order_code: order.value.code, item_id: itemId },
  })
  const result = onResponse(res)
  if (result) {
    order.value.items = order.value.items?.filter((it) => it.id !== itemId)
  }
}

const editOrderDialog = ref(false)
const updateOrder = async (body: ManufacturingOrderCreateOrUpdateSchema) => {
  if (!order.value) return
  const result = await warehouseApiRoutesManufacturingOrdersUpdateManufacturingOrder({
    body,
    path: { order_code: order.value.code },
  })
  const updated = onResponse(result)
  if (updated) {
    order.value = updated.data
    editOrderDialog.value = false
  }
}

const transition = async (action: 'next' | 'cancel') => {
  if (!order.value) return
  const res = await warehouseApiRoutesManufacturingOrdersTransitionManufacturingOrder({
    path: { order_code: order.value.code },
    body: { action },
  })
  const updated = onResponse(res)
  if (updated) {
    order.value = updated.data
  }
}

const confirmDialog = ref(false)
const confirm = async () => {
  await transition('next')
  confirmDialog.value = false
}

const startDialog = ref(false)
const startProduction = async () => {
  await transition('next')
  startDialog.value = false
}

const completeDialog = ref(false)
const complete = async () => {
  await transition('next')
  completeDialog.value = false
}

const cancelDialog = ref(false)
const cancel = async () => {
  await transition('cancel')
  cancelDialog.value = false
}
</script>
