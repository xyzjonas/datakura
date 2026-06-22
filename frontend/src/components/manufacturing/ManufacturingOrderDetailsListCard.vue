<template>
  <ForegroundPanel class="flex flex-col">
    <template #header>
      <span class="text-xs text-muted">INFORMACE O DOKLADU</span>
    </template>
    <q-list dense class="mt-2" separator>
      <q-item clickable>
        <q-item-section>Číslo dokladu</q-item-section>
        <q-item-section avatar>
          <span class="flex gap-1">
            <span class="font-bold">{{ order.code }}</span>
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </span>
        </q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Popis</q-item-section>
        <q-item-section avatar>{{ order.description }}</q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Typ</q-item-section>
        <q-item-section avatar>
          <q-badge :color="order.is_external ? 'orange-8' : 'teal-7'">
            {{ order.is_external ? 'Externí' : 'Interní' }}
          </q-badge>
        </q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Dodavatel / výrobce</q-item-section>
        <q-item-section avatar>{{ order.supplier?.name }}</q-item-section>
      </q-item>
      <q-item v-if="order.customer" clickable>
        <q-item-section>Pracoviště</q-item-section>
        <q-item-section avatar>{{ order.customer.name }}</q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Datum dokončení</q-item-section>
        <q-item-section avatar>{{ formatDateLong(order.completed_date) }}</q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Datum zrušení</q-item-section>
        <q-item-section avatar>{{ formatDateLong(order.cancelled_date) }}</q-item-section>
      </q-item>
    </q-list>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { ManufacturingOrderSchema } from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import { formatDateLong } from '@/utils/date'

defineProps<{ order: ManufacturingOrderSchema }>()
</script>
