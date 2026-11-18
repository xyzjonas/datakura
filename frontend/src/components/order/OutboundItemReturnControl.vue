<template>
  <div v-if="selection?.active.value && max > 0" class="flex items-center gap-1 justify-end">
    <q-badge v-if="amount > 0" color="warning" text-color="dark" data-test="return-batch-badge">
      k vrácení: {{ amount }} {{ item.product.unit }}
    </q-badge>
    <q-btn
      flat
      dense
      no-caps
      color="primary"
      icon="sym_o_assignment_return"
      :label="amount > 0 ? 'změnit' : 'vrátit'"
      data-test="return-item-button"
      @click="dialog = true"
    />
    <q-btn
      v-if="amount > 0"
      flat
      dense
      round
      color="negative"
      icon="sym_o_close"
      data-test="return-item-remove"
      @click="amount = 0"
    >
      <q-tooltip>Odebrat z vratky</q-tooltip>
    </q-btn>
    <ReturnItemDialog v-model:show="dialog" v-model:amount="amount" :item="item" :max="max" />
  </div>
</template>

<script setup lang="ts">
import type { OutboundOrderItemSchema } from '@/client'
import { returnableAmount, useReturnSelection } from '@/composables/use-return-selection'
import { computed, ref } from 'vue'
import ReturnItemDialog from './ReturnItemDialog.vue'

const props = defineProps<{ item: OutboundOrderItemSchema }>()

const selection = useReturnSelection()
const dialog = ref(false)
const max = computed(() => returnableAmount(props.item))

// the part of this row collected for the return so far
const amount = computed({
  get: () => selection?.amountOf(props.item.index) ?? 0,
  set: (value: number) => selection?.set(props.item.index, value),
})
</script>
