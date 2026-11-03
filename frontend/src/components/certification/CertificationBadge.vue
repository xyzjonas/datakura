<template>
  <q-badge
    v-if="requiresCertification"
    :color="certification ? 'positive' : 'orange'"
    class="py-0.5"
    data-test="certification-badge"
  >
    <q-icon name="sym_o_verified" class="mr-1" size="14px" />
    {{ certification ? certification.code : 'chybí certifikát' }}
  </q-badge>
</template>

<script setup lang="ts">
defineProps<{
  requiresCertification?: boolean
  certification?: { code: string } | null
}>()
</script>
