<template>
  <a class="link w-30 truncate block" @click="onClick">
    {{ customer?.name ?? 'Neznámý zákazník' }}
  </a>
</template>

<script setup lang="ts">
import type { CustomerSchema } from '@/client'
import { useAppRouter } from '@/composables/use-app-router'

const props = defineProps<{ customer?: Pick<CustomerSchema, 'code' | 'name'> }>()

const { goToCustomer } = useAppRouter()
const onClick = () => {
  if (props.customer?.code) {
    goToCustomer(props.customer.code)
  }
}
</script>

<style lang="scss" scoped></style>
