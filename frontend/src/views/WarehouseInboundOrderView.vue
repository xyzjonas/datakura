<template>
  <div v-if="order" class="flex flex-col gap-2 flex-1">
    <div class="flex justify-between flex-wrap">
      <q-breadcrumbs class="mb-5 flex-[3]">
        <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Příjemky" :to="{ name: 'warehouseInboundOrders' }" />
        <q-breadcrumbs-el :label="order.code" />
      </q-breadcrumbs>
      <div class="flex flex-col items-end gap-3 flex-1">
        <OrderProgress :order="order" class="flex-1 h-6 w-full" />
        <q-btn flat color="primary" icon-right="sym_o_query_stats" @click="auditDialog = true">
          <q-tooltip :offset="[0, 10]">Zobrazit historii</q-tooltip>
        </q-btn>
      </div>
    </div>

    <div class="mb-2 flex gap-2 justify-between items-center">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">PŘÍJEMKA</span>
          <h1 class="text-primary mb-1 text-5xl">{{ order.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ order.code }}</h5>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </div>
        </div>
        <div class="min-w-xs flex flex-col gap-2 items-start">
          <InboundWarehouseOrderStateBadge :state="order.state" />
        </div>
      </div>
      <div class="flex gap-2 items-center">
        <q-btn
          v-if="order.state === 'in transit'"
          unelevated
          color="primary"
          icon="sym_o_local_shipping"
          label="potvrdit příjezd"
          @click="confirmDialog = true"
          class="ml-auto"
        />
        <q-btn
          v-else-if="step === 1"
          unelevated
          color="positive"
          icon="sym_o_order_approve"
          label="potvrdit"
          @click="confirmDialog = true"
          class="ml-auto"
        />
        <MissingMarker
          v-if="step === 2"
          text="#TODO: změna tam a zpět? Přepočet ceny by měl proběhnout zde."
          class="text-nowrap"
        >
          <q-btn
            v-if="step === 2"
            unelevated
            color="primary"
            icon="sym_o_restart_alt"
            label="editovat"
            @click="resetDialog = true"
            class="ml-auto"
          />
        </MissingMarker>
      </div>
    </div>
    <div class="flex gap-2">
      <CustomerCard :customer="order.order.supplier" title="Dodavatel" class="flex-[3]" />
      <LinkedEntitiesCard
        show-inbound-order
        :inbound-order="order.order"
        show-credit-note
        :credit-note="order.credit_note"
        :show-parent-warehouse-order="!!order.parent_order"
        :parent-warehouse-order="order.parent_order"
        :show-child-warehouse-orders="!!order.child_orders?.length"
        :child-warehouse-orders="order.child_orders"
        class="flex-1"
      />
    </div>

    <ForegroundPanel v-if="order.state != 'in transit'">
      <InboundWarehouseOrderTimeline :order="order" />
    </ForegroundPanel>

    <LargeTabs
      v-if="order.state != 'in transit'"
      v-model:tab="activeTabKey"
      :items="[
        {
          key: 'todo',
          icon: 'sym_o_call_received',
          title: `${todoItems.length} položky k naskladnění`,
        },
        { key: 'outbound', icon: 'sym_o_call_made', title: `${movements.length} Provedené Pohyby` },
      ]"
      class="my-5"
    />
    <!-- REMAINING ITEMS -->
    <InboundWarehouseOrderItemsList
      v-if="activeTabKey === 'todo'"
      :items="todoItems"
      :readonly="order.state !== 'draft'"
      :allow-move="order.state === 'pending' || order.state === 'started'"
      :warehouse-order-code="order.code"
      @packaged="updateOrderItems"
      @dissolve-item="dissolveItem"
      @remove-item="removeItem"
      @moved="moveItem"
      @offloaded="fetchOrder"
    ></InboundWarehouseOrderItemsList>

    <!-- MOVEMENTS -->
    <TransitionGroup v-if="activeTabKey === 'outbound'" name="list" tag="div" class="flex">
      <WarehouseMovementItem
        v-for="(movement, index) in movements"
        :key="index"
        :index="index + 1"
        :movement="movement"
      />
      <q-item v-if="movements.length === 0">
        <q-item-section>
          <q-item-label caption>Žádné pohyby nebyly zaznamenány.</q-item-label>
        </q-item-section>
      </q-item>
    </TransitionGroup>

    <ConfirmDialog
      v-model:show="confirmDialog"
      :title="order.state === 'in transit' ? 'Potvrdit příjezd zboží' : 'Potvrdit příjemku'"
      @confirm="onConfirmDialog"
    >
      <div v-if="order.state === 'in transit'" class="flex flex-col gap-4">
        <span>
          Příjemka bude označena jako <InboundWarehouseOrderStateBadge state="draft" /> a vytvoří se
          položky na zvoleném příjmovém místě.
        </span>
        <ReceivingLocationSelect v-model="arrivalLocationCode" />
      </div>
      <span v-else>
        Příjemka bude označena jako <InboundWarehouseOrderStateBadge state="pending" /> a pracovník
        na příjmu může začít s přesunem zboží. Po tomto kroku již nebude možné příjemku upravovat.
      </span>
    </ConfirmDialog>
    <ConfirmDialog
      v-model:show="resetDialog"
      title="Resetovat příjemku"
      @confirm="transitionOrder('draft')"
    >
      <span>
        Příjemka bude zpátky označena jako <InboundWarehouseOrderStateBadge state="draft" /> a bude
        možné ji opět editovat. Pracovník na příjmu nebude schopen pokračovat s přesunem zboží.<br /><small
          >Není možné vrátit rozpracovanou příjemku.</small
        >
      </span>
    </ConfirmDialog>
    <AuditLogDialog
      v-model:show="auditDialog"
      source="warehouse-inbound-order"
      :code="order.code"
      title="Historie stavu příjemky"
    />
  </div>
</template>

<script setup lang="ts">
import {
  type InboundWarehouseOrderSchema,
  warehouseApiRoutesWarehouseDissolveInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseGetInboundWarehouseOrder,
  warehouseApiRoutesWarehousePutawayInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseRemoveFromOrderToCreditNote,
  warehouseApiRoutesWarehouseTrackInboundWarehouseOrderItem,
  warehouseApiRoutesWarehouseTransitionInboundWarehouseOrder,
  type WarehouseItemSchema,
  type WarehouseLocationSchema,
} from '@/client'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import LargeTabs from '@/components/LargeTabs.vue'
import MissingMarker from '@/components/MissingMarker.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import OrderProgress from '@/components/OrderProgress.vue'
import InboundWarehouseOrderItemsList from '@/components/putaway/InboundWarehouseOrderItemsList.vue'
import InboundWarehouseOrderStateBadge from '@/components/putaway/InboundWarehouseOrderStateBadge.vue'
import InboundWarehouseOrderTimeline from '@/components/putaway/InboundWarehouseOrderTimeline.vue'
import ReceivingLocationSelect from '@/components/selects/ReceivingLocationSelect.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import WarehouseMovementItem from '@/components/warehouse/WarehouseMovementItem.vue'
import { useApi } from '@/composables/use-api'
import { getInboundWarehouseOrderStep } from '@/constants/inbound-warehouse-order'
import { useQuasar } from 'quasar'
import { computed, ref } from 'vue'

const props = defineProps<{ code: string }>()

const { onResponse } = useApi()
const $q = useQuasar()

const activeTabKey = ref('todo')

const response = await warehouseApiRoutesWarehouseGetInboundWarehouseOrder({
  path: { code: props.code },
})
const data = onResponse(response)

const order = ref<InboundWarehouseOrderSchema>()
if (data) {
  order.value = data.data
}

const todoItems = computed(() => (order.value?.items ?? []).filter((it) => it.location.is_putaway))
const movements = computed(() => order.value?.movements ?? [])

const step = computed(() => getInboundWarehouseOrderStep(order.value))
const arrivalLocationCode = ref<string>()

const updateOrderItems = async (item: WarehouseItemSchema, toBeAdded: WarehouseItemSchema[]) => {
  if (!order.value) {
    return
  }
  const response = await warehouseApiRoutesWarehouseTrackInboundWarehouseOrderItem({
    path: {
      code: order.value.code,
      item_code: item.product.code,
    },
    body: {
      to_be_added: toBeAdded,
    },
  })
  const data = onResponse(response)
  if (data) {
    order.value = data.data
  }
}

const confirmDialog = ref(false)
const resetDialog = ref(false)
const auditDialog = ref(false)
const transitionOrder = async (
  state: 'pending' | 'draft',
  locationCode: string | undefined = undefined,
) => {
  if (!order.value) {
    return
  }

  if (state === 'draft' && order.value.state === 'in transit' && !locationCode) {
    $q.notify({
      type: 'negative',
      message: 'Vyberte příjmové místo',
    })
    return
  }

  const data = onResponse(
    await warehouseApiRoutesWarehouseTransitionInboundWarehouseOrder({
      path: { code: order.value.code },
      body: {
        state: state,
        location_code: locationCode,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
  $q.notify({
    type: 'positive',
    message: 'Nový stav zaznamenán',
    caption: `Příjemka ${order.value.code}`,
  })
}

const onConfirmDialog = async () => {
  if (order.value?.state === 'in transit') {
    await transitionOrder('draft', arrivalLocationCode.value)
    return
  }

  await transitionOrder('pending')
}

const dissolveItem = async (itemId: number) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseDissolveInboundWarehouseOrderItem({
      path: {
        code: order.value.code,
        item_id: itemId,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
}

const removeItem = async (itemId: number, amount: number) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehouseRemoveFromOrderToCreditNote({
      path: {
        code: order.value.code,
      },
      body: {
        item_id: itemId,
        amount: amount,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
  $q.notify({
    type: 'positive',
    message: `${amount} MJ odstraněno z příjemky`,
    caption: `Evidováno v dobropisu ${order.value.credit_note?.code ?? 'N/A'}`,
  })
}

const moveItem = async (itemCode: number, location: WarehouseLocationSchema) => {
  if (!order.value) {
    return
  }
  const data = onResponse(
    await warehouseApiRoutesWarehousePutawayInboundWarehouseOrderItem({
      path: {
        code: order.value.code,
        item_id: itemCode,
      },
      body: {
        new_location_code: location.code,
      },
    }),
  )
  if (data) {
    order.value = data.data
  }
  $q.notify({
    type: 'positive',
    message: `Položka úspěšně přesunuta`,
    caption: `'${itemCode}' se nyní nachází na skladovém místě ${location.code}`,
  })
}

const fetchOrder = async () => {
  if (!order.value) return
  const res = await warehouseApiRoutesWarehouseGetInboundWarehouseOrder({
    path: { code: order.value.code },
  })
  const data = onResponse(res)
  if (data) {
    order.value = data.data
  }
}
</script>

<style lang="scss" scoped></style>
