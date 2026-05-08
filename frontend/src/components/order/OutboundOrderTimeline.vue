<template>
  <foreground-panel>
    <template #header>
      <span class="uppercase text-xs text-muted">Stav objednávky</span>
    </template>

    <div class="flex flex-row w-full items-start py-3">
      <template v-for="(s, i) in visibleSteps" :key="s.step">
        <div class="flex flex-col items-center flex-1 min-w-0">
          <div class="flex items-center w-full">
            <div
              class="flex-1 h-0.5 transition-colors"
              :class="i === 0 ? 'invisible' : lineClass(s.step)"
            />
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors"
              :class="circleClass(s.step)"
            >
              <q-icon
                :name="
                  isCancelled && step >= s.step
                    ? 'sym_o_block'
                    : isDone(s.step)
                      ? 'sym_o_check'
                      : s.icon
                "
                size="xs"
              />
            </div>
            <div
              class="flex-1 h-0.5 transition-colors"
              :class="i === visibleSteps.length - 1 ? 'invisible' : lineClass(s.step + 1)"
            />
          </div>
          <div class="flex flex-col items-center text-center mt-2 px-1 gap-0.5">
            <span class="text-xs font-600 leading-tight" :class="textClass(s.step)">{{
              s.title
            }}</span>
            <span class="text-2xs text-muted leading-tight italic">{{ s.caption }}</span>
          </div>
        </div>
      </template>
    </div>
  </foreground-panel>
</template>

<script setup lang="ts">
import type { OutboundOrderSchema } from '@/client'
import { CANCELLED, OUTBOUND_ORDER_STATES } from '@/constants/outbound-order'
import { computed } from 'vue'
import ForegroundPanel from '../ForegroundPanel.vue'
import { useQuasar } from 'quasar'

const STEPS = [
  { step: 1, title: 'Koncept', caption: 'Čeká na potvrzení', icon: 'sym_o_ink_pen' },
  {
    step: 2,
    title: 'Potvrzeno',
    caption: 'Objednávka potvrzena',
    icon: 'sym_o_approval_delegation',
  },
  { step: 3, title: 'Kompletace', caption: 'Zboží se kompletuje', icon: 'sym_o_handyman' },
  { step: 4, title: 'Odesláno', caption: 'Výdejka dokončena', icon: 'sym_o_send' },
  { step: 5, title: 'Vyfakturováno', caption: 'Faktura vystavena', icon: 'sym_o_receipt_long' },
  {
    step: 6,
    title: 'Čeká na úhradu',
    caption: 'Po splatnosti bez úhrady',
    icon: 'sym_o_hourglass_top',
  },
  {
    step: 7,
    title: 'Dokončeno / uhrazeno',
    caption: 'Objednávka uzavřena',
    icon: 'sym_o_check_circle',
  },
]

const props = defineProps<{ order: Pick<OutboundOrderSchema, 'state'> }>()
const $q = useQuasar()

const step = computed(() => OUTBOUND_ORDER_STATES[props.order.state]?.step ?? CANCELLED)
const isCancelled = computed(() => step.value >= CANCELLED)

const isDone = (stepNum: number) => !isCancelled.value && step.value > stepNum

const visibleSteps = computed(() =>
  STEPS.filter((s) => {
    if (step.value === s.step) return true
    if ($q.screen.gt.md) return true
    if ($q.screen.gt.sm) {
      return Math.abs(step.value - s.step) <= 2
    }
    return Math.abs(step.value - s.step) <= 1
  }),
)

const lineClass = (stepNum: number) => {
  if (isCancelled.value) return 'bg-negative'
  if (step.value >= stepNum) return 'bg-positive'
  return 'bg-gray-3'
}

const circleClass = (stepNum: number) => {
  if (isCancelled.value && step.value >= stepNum) return 'bg-negative text-white'
  if (isDone(stepNum)) return 'bg-positive text-white'
  if (step.value === stepNum) return 'bg-accent text-white'
  return 'bg-gray-3 text-gray-6'
}

const textClass = (stepNum: number) => {
  if (isCancelled.value && step.value >= stepNum) return 'text-negative'
  if (isDone(stepNum)) return 'text-positive'
  if (step.value === stepNum) return 'text-accent'
  return 'text-gray-5'
}
</script>
