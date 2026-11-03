<template>
  <router-link
    v-if="link && certification?.id !== undefined"
    :to="{ name: 'certificationDetail', params: { id: certification.id } }"
    class="no-underline"
    data-test="certification-badge-link"
    @click.stop
  >
    <q-badge color="positive" class="py-0.5 cursor-pointer" data-test="certification-badge">
      <q-icon name="sym_o_verified" class="mr-1" size="14px" />
      {{ certification.code }}
    </q-badge>
  </router-link>
  <q-badge
    v-else-if="requiresCertification"
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
  certification?: { id?: number; code: string } | null
  /** Render certified goods as a link to the certification detail. */
  link?: boolean
}>()
</script>
