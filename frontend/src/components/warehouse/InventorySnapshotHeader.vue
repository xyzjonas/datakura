<template>
  <ForegroundPanel no-padding>
    <div class="grid divide-x divide-y sm:grid-cols-2 xl:grid-cols-5 xl:divide-y-0">
      <InventorySnapshotHeaderCell label="Skladových položek">
        <span class="text-xl font-semibold">{{ snapshot.line_count }}</span>
      </InventorySnapshotHeaderCell>

      <InventorySnapshotHeaderCell
        :label="
          valuationMode === 'purchase'
            ? 'Hodnota skladu (při uložení)'
            : 'Hodnota skladu (při příjmu)'
        "
      >
        <InventorySnapshotCurrencyValues
          :totals="
            valuationMode === 'purchase' ? snapshot.purchase_totals : snapshot.receipt_totals
          "
          empty-label="Žádné oceněné položky"
        />
      </InventorySnapshotHeaderCell>

      <InventorySnapshotHeaderCell
        label="Výdaje (nákupy)"
        caption="Uzavřené nákupy od minulého stavu"
      >
        <template #action>
          <q-btn flat dense round size="sm" icon="sym_o_list" @click="showInbound = true">
            <q-tooltip>Zobrazit objednávky</q-tooltip>
          </q-btn>
        </template>
        <InventorySnapshotCurrencyValues :totals="snapshot.expenditure_totals" />
      </InventorySnapshotHeaderCell>

      <InventorySnapshotHeaderCell
        label="Příjmy (výdeje)"
        caption="Celková cena výdeje uzavřených výdejek"
      >
        <template #action>
          <q-btn flat dense round size="sm" icon="sym_o_list" @click="showOutbound = true">
            <q-tooltip>Zobrazit výdejky</q-tooltip>
          </q-btn>
        </template>
        <InventorySnapshotCurrencyValues :totals="snapshot.gain_totals" />
      </InventorySnapshotHeaderCell>

      <InventorySnapshotHeaderCell label="Hrubý zisk" caption="Příjmy − výdaje">
        <InventorySnapshotCurrencyValues :totals="grossGain" signed />
      </InventorySnapshotHeaderCell>
    </div>

    <InventorySnapshotOrdersDialog
      v-model:show="showInbound"
      title="Uzavřené nákupy"
      subtitle="Přijaté objednávky uzavřené od minulého stavu skladu"
      :orders="snapshot.inbound_orders"
      route-name="inboundOrderDetail"
      empty-label="Žádné uzavřené objednávky"
    />
    <InventorySnapshotOrdersDialog
      v-model:show="showOutbound"
      title="Uzavřené výdejky"
      subtitle="Výdejky uzavřené od minulého stavu skladu, hodnota = celková cena výdeje"
      :orders="snapshot.outbound_orders"
      route-name="warehouseOutboundOrderDetail"
      empty-label="Žádné uzavřené výdejky"
    />
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { InventorySnapshotDetailSchema } from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import InventorySnapshotCurrencyValues from '@/components/warehouse/InventorySnapshotCurrencyValues.vue'
import InventorySnapshotHeaderCell from '@/components/warehouse/InventorySnapshotHeaderCell.vue'
import InventorySnapshotOrdersDialog from '@/components/warehouse/InventorySnapshotOrdersDialog.vue'
import {
  getSnapshotGrossGain,
  type InventorySnapshotValuationMode,
} from '@/views/inventory-snapshot'
import { computed, ref } from 'vue'

const props = defineProps<{
  snapshot: InventorySnapshotDetailSchema
  valuationMode: InventorySnapshotValuationMode
}>()

const showInbound = ref(false)
const showOutbound = ref(false)

const grossGain = computed(() => getSnapshotGrossGain(props.snapshot))
</script>
