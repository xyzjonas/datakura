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
        <q-item-section>Číslo objednávky zákazníka</q-item-section>
        <q-item-section avatar>
          <span class="flex gap-1">
            {{ order.external_code }}
            <CopyToClipBoardButton v-if="order.external_code" :text="order.external_code" />
          </span>
        </q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Popis</q-item-section>
        <q-item-section avatar>{{ order.description }}</q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Měna objednávky</q-item-section>
        <q-item-section avatar>{{ order.currency }}</q-item-section>
      </q-item>

      <q-item clickable>
        <q-item-section>Požadovaný termín dodání</q-item-section>
        <q-item-section avatar>{{ formatDateLong(order.requested_delivery_date) }}</q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Zboží přijato</q-item-section>
        <q-item-section avatar>{{ formatDateLong(order.received_date) }}</q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Datum zrušení</q-item-section>
        <q-item-section avatar>{{ formatDateLong(order.cancelled_date) }}</q-item-section>
      </q-item>
    </q-list>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { InboundOrderSchema } from '@/client'
import ForegroundPanel from '../ForegroundPanel.vue'
import { formatDateLong } from '@/utils/date'
import CopyToClipBoardButton from '../CopyToClipBoardButton.vue'

defineProps<{ order: InboundOrderSchema }>()
</script>

<style lang="scss" scoped></style>
