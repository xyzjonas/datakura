<template>
  <ForegroundPanel class="flex flex-col min-w-[400px] flex-[2]">
    <q-list dense class="mt-2" separator>
      <q-item clickable>
        <q-item-section>Číslo dokladu</q-item-section>
        <q-item-section avatar>
          <span class="flex gap-1">
            {{ order.code }}
            <CopyToClipBoardButton v-if="order.code" :text="order.code" />
          </span>
        </q-item-section>
      </q-item>
      <q-item clickable>
        <q-item-section>Externí číslo</q-item-section>
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
      <q-item v-if="order.note">
        <div class="description overflow-y-auto h-30 w-full">{{ order.note }}</div>
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
