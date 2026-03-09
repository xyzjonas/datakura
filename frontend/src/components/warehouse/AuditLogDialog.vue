<template>
  <RightSideDialog v-model:show="showDialog" :title="title" :panel-class="panelClass">
    <div v-if="loading" class="h-full min-h-[240px] flex items-center justify-center">
      <q-spinner color="primary" size="32px" />
    </div>

    <WarehouseItemAuditTimeline v-else :entries="entries" class="p-5" />

    <template #footer>
      <div class="flex justify-end">
        <q-btn flat color="primary" label="Zavřít" @click="showDialog = false" />
      </div>
    </template>
  </RightSideDialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesInboundOrdersGetInboundOrderAudits,
  warehouseApiRoutesProductGetProductAudits,
  warehouseApiRoutesWarehouseGetInboundWarehouseOrderAudits,
  type GetAuditTimelineResponse,
} from '@/client'
import RightSideDialog from '@/components/layout/RightSideDialog.vue'
import WarehouseItemAuditTimeline from '@/components/warehouse/WarehouseItemAuditTimeline.vue'
import { useApi } from '@/composables/use-api'
import { ref, watch } from 'vue'

type AuditSource = 'inbound-order' | 'warehouse-inbound-order' | 'product'

type Props = {
  source: AuditSource
  code: string
  title?: string
  panelClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Audit Log',
  panelClass: 'w-[min(100vw,780px)]',
})

const showDialog = defineModel<boolean>('show', { default: false })

const { onResponse } = useApi()

const entries = ref<GetAuditTimelineResponse['data']>([])
const loading = ref(false)

const fetchAudits = async () => {
  if (!props.code) {
    entries.value = []
    return
  }

  loading.value = true
  try {
    if (props.source === 'warehouse-inbound-order') {
      const response = await warehouseApiRoutesWarehouseGetInboundWarehouseOrderAudits({
        path: { code: props.code },
      })
      const payload = onResponse(response)
      entries.value = payload?.data ?? []
      return
    }

    if (props.source === 'product') {
      const response = await warehouseApiRoutesProductGetProductAudits({
        path: { product_code: props.code },
      })
      const payload = onResponse(response)
      entries.value = payload?.data ?? []
      return
    }

    const response = await warehouseApiRoutesInboundOrdersGetInboundOrderAudits({
      path: { order_code: props.code },
    })
    const payload = onResponse(response)
    entries.value = payload?.data ?? []
  } finally {
    loading.value = false
  }
}

watch(
  () => [showDialog.value, props.source, props.code] as const,
  async ([open]) => {
    if (!open) {
      return
    }
    await fetchAudits()
  },
  { immediate: false },
)
</script>
