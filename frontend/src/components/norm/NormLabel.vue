<template>
  <span v-if="norm" class="inline-flex items-center gap-1 flex-nowrap whitespace-nowrap">
    <span data-test="norm-label">{{ norm.label }}</span>
    <q-btn
      v-if="norm.equivalents.length"
      flat
      dense
      round
      size="xs"
      icon="sym_o_sync_alt"
      color="grey"
      data-test="norm-aliases-btn"
      @click.stop
    >
      <q-popup-proxy>
        <q-card class="p-3 min-w-48">
          <div class="text-xs text-muted mb-1 uppercase">Ekvivalentní normy</div>
          <ul class="m-0 p-0 list-none" data-test="norm-aliases">
            <li v-for="alias in norm.equivalents" :key="alias.id">{{ alias.label }}</li>
          </ul>
        </q-card>
      </q-popup-proxy>
    </q-btn>
  </span>
  <span v-else class="text-gray-5">-</span>
</template>

<script setup lang="ts">
import type { NormSchema } from '@/client'

defineProps<{ norm?: NormSchema | null }>()
</script>
