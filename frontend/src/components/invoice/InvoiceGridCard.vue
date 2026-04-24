<template>
  <ForegroundPanel class="flex flex-col gap-3">
    <div class="flex items-start justify-between gap-3">
      <div>
        <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Faktura</div>
        <button
          class="mt-2 text-left text-xl font-semibold text-primary"
          @click="goToInvoice(invoice.code)"
        >
          {{ invoice.code }}
        </button>
      </div>
      <div class="text-right text-sm text-gray-6">
        <div>{{ invoice.issued_date }}</div>
        <div>splatnost {{ invoice.due_date }}</div>
      </div>
    </div>

    <div>
      <div class="text-xs uppercase tracking-[0.16em] text-gray-5">{{ partnerLabel }}</div>
      <div class="mt-1 font-semibold text-slate-8">{{ partnerName }}</div>
    </div>

    <div class="grid gap-2 text-sm text-gray-6 sm:grid-cols-3">
      <div>
        <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Platební metoda</div>
        <div class="mt-1 font-medium text-slate-8">{{ invoice.payment_method.name }}</div>
      </div>
      <div>
        <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Měna</div>
        <div class="mt-1 font-medium text-slate-8">{{ invoice.currency }}</div>
      </div>
      <div>
        <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Externí kód</div>
        <div class="mt-1 font-medium text-slate-8">{{ invoice.external_code || '-' }}</div>
      </div>
    </div>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { InvoiceSchema } from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import { useAppRouter } from '@/composables/use-app-router'
import { computed } from 'vue'

const props = defineProps<{
  invoice: InvoiceSchema
  direction: 'inbound' | 'outbound'
}>()

const { goToInvoice } = useAppRouter()

const partnerLabel = computed(() => (props.direction === 'outbound' ? 'Odběratel' : 'Dodavatel'))

const partnerName = computed(() => {
  const partner = props.direction === 'outbound' ? props.invoice.customer : props.invoice.supplier
  return partner?.name ?? '-'
})
</script>
