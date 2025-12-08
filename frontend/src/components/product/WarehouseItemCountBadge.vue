<template>
  <q-badge class="text-[14px]" :color="item.amount < packageAmount ? 'accent' : 'positive'">
    <span v-decimal="item.amount"></span>
    <span v-if="isPackaged" class="mx-1">/</span>
    <span v-if="isPackaged" v-decimal="packageAmount"></span>
  </q-badge>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ item: WarehouseItemSchema }>()
const isPackaged = computed(
  () => props.item.package?.amount && props.item.amount <= props.item.package.amount,
)
const packageAmount = computed(() => (props.item.package ? props.item.package.amount : 0))
</script>

<style lang="scss" scoped></style>
