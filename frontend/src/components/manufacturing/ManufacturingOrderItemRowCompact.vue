<template>
  <div
    v-if="cardLayout"
    class="w-full flex flex-col gap-2.5 p-3.5 rounded-xl border border-solid light:bg-white shadow-sm light:border-slate-200 dark:border-gray-7"
    data-test="order-item-card"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-start gap-2 flex-1 min-w-0">
        <span
          class="inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-semibold rounded border border-solid shrink-0 light:text-slate-600 light:bg-slate-100 light:border-slate-200 dark:border-gray-7"
          data-test="item-index"
          >#{{ item.index + 1 }}</span
        >
        <div class="flex flex-col min-w-0">
          <ProductCell :product="item.in_product" />
          <ManufacturingItemRequirementBadges :item="item" class="mt-1" />
        </div>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        <EditIconButton class="min-w-9 min-h-9" :disable="readonly" @click="emit('edit')" />
        <CloseIconButton class="min-w-9 min-h-9" :disable="readonly" @click="removeDialog = true" />
      </div>
    </div>

    <div
      class="flex items-center justify-between px-2.5 py-1.5 rounded-lg light:bg-slate-50 dark:bg-dark-6"
      data-test="item-in-amount"
    >
      <div class="flex items-center gap-2 text-xs">
        <q-icon name="sym_o_inventory_2" size="1rem" color="primary" />
        <span class="font-semibold tabular-nums">
          {{ item.in_amount }} {{ item.in_product.unit }}
        </span>
      </div>
    </div>

    <div class="pt-1 flex flex-col gap-1.5 border-0 border-t border-solid light:border-slate-100">
      <ProductCell :product="item.out_product" />
      <span class="text-base font-bold tabular-nums" data-test="item-out-amount">
        {{ item.out_amount }} {{ item.out_product.unit }}
      </span>
    </div>
  </div>
  <div v-else class="flex flex-col flex-1 gap-2">
    <div class="flex items-center w-full flex-nowrap">
      <div class="w-12">
        <IndexRectangle :index="item.index + 1" />
      </div>
      <!-- Input product -->
      <div class="w-xs">
        <ProductCell :product="item.in_product" />
        <ManufacturingItemRequirementBadges :item="item" class="mt-1" />
      </div>

      <div class="grid items-center grid-cols-4 flex-1 text-right">
        <!-- Input amount -->
        <div class="flex flex-col" data-test="item-in-amount">
          <span class="text-lg font-bold tabular-nums">{{ item.in_amount }}</span>
          <div class="text-xs text-gray-5">
            {{ item.in_amount }} x <q-badge color="gray">{{ item.in_product.unit }}</q-badge>
          </div>
        </div>

        <!-- Output product -->
        <div class="flex flex-col items-end" data-test="item-out-product">
          <ProductCell :product="item.out_product" class="items-end" />
        </div>

        <!-- Output amount -->
        <div class="flex flex-col" data-test="item-out-amount">
          <span class="text-lg font-bold tabular-nums">{{ item.out_amount }}</span>
          <div class="text-xs text-gray-5">
            {{ item.out_amount }} x <q-badge color="gray">{{ item.out_product.unit }}</q-badge>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-1 justify-end">
          <EditIconButton :disable="readonly" @click="emit('edit')">
            <q-tooltip>Upravit</q-tooltip>
          </EditIconButton>
          <CloseIconButton :disable="readonly" @click="removeDialog = true">
            <q-tooltip>Odebrat</q-tooltip>
          </CloseIconButton>
        </div>
      </div>
    </div>
  </div>

  <ConfirmDialog v-model:show="removeDialog" title="Odebrat položku" @confirm="emit('remove')">
    Opravdu odebrat položku <strong>{{ item.in_product.name }}</strong
    >?
  </ConfirmDialog>
</template>

<script setup lang="ts">
import type { ManufacturingOrderItemSchema } from '@/client'
import { useOrderItemCardLayout } from '@/composables/use-order-item-card-layout'
import { ref } from 'vue'
import CloseIconButton from '../common/buttons/CloseIconButton.vue'
import EditIconButton from '../common/buttons/EditIconButton.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import IndexRectangle from '../IndexRectangle.vue'
import ManufacturingItemRequirementBadges from './ManufacturingItemRequirementBadges.vue'
import ProductCell from './ManufacturingItemProductCell.vue'

defineProps<{ item: ManufacturingOrderItemSchema; readonly?: boolean }>()

const emit = defineEmits<{ (e: 'edit'): void; (e: 'remove'): void }>()

const cardLayout = useOrderItemCardLayout()
const removeDialog = ref(false)
</script>
