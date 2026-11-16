<template>
  <div class="flex flex-col gap-3" data-test="item-certification">
    <div
      v-if="item.certification && !editing"
      class="flex items-start gap-3 rounded border p-3 border-positive"
    >
      <q-icon name="sym_o_verified" color="positive" size="24px" />
      <div class="flex flex-col flex-1 min-w-0 gap-0.5">
        <span class="font-semibold">{{ item.certification.code }}</span>
        <span v-if="item.certification.description" class="text-xs text-gray-6">
          {{ item.certification.description }}
        </span>
        <CertificationFileLink :attachment="item.certification.attachment" />
        <div v-if="item.batch_code" class="mt-1">
          <BatchBadge :batch-code="item.batch_code" />
        </div>
      </div>
      <div class="flex gap-1">
        <q-btn flat dense no-caps label="Změnit" @click="editing = true" :disable="readonly" />
        <q-btn
          flat
          dense
          no-caps
          color="negative"
          label="Odebrat"
          :disable="readonly"
          @click="remove"
        />
      </div>
    </div>

    <q-form v-else class="flex flex-col gap-3" @submit="submit">
      <div
        v-if="!item.certification"
        class="flex items-center gap-2 text-sm text-orange"
        data-test="certification-missing"
      >
        <q-icon name="sym_o_warning" size="18px" />
        Před potvrzením objednávky je nutné doplnit certifikát.
      </div>

      <CertificationFields v-model:draft="draft" />

      <div class="flex justify-end gap-2">
        <q-btn v-if="item.certification" flat no-caps label="Zrušit" @click="editing = false" />
        <q-btn unelevated no-caps color="primary" label="uložit certifikát" type="submit" />
      </div>
    </q-form>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesInboundOrdersRemoveInboundOrderItemCertification,
  warehouseApiRoutesInboundOrdersSetInboundOrderItemCertification,
  type InboundOrderItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { ref } from 'vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import CertificationFileLink from './CertificationFileLink.vue'
import CertificationFields from './CertificationFields.vue'
import {
  certificationDraftToBody,
  emptyCertificationDraft,
  multipartRequestOptions,
  type CertificationDraft,
} from './certification-upload'

const { onResponse } = useApi()

const props = defineProps<{ orderCode: string; readonly?: boolean }>()

const item = defineModel<InboundOrderItemSchema>('item', { required: true })

const editing = ref(false)
const draft = ref<CertificationDraft>(emptyCertificationDraft())

const path = () => ({ order_code: props.orderCode, item_index: item.value.index })

const submit = async () => {
  const body = certificationDraftToBody(draft.value)
  if (!body) return
  const res = await warehouseApiRoutesInboundOrdersSetInboundOrderItemCertification({
    path: path(),
    body,
    ...multipartRequestOptions,
  })
  const data = onResponse(res)
  if (data?.data) {
    item.value = data.data
    editing.value = false
    draft.value = emptyCertificationDraft()
  }
}

const remove = async () => {
  const res = await warehouseApiRoutesInboundOrdersRemoveInboundOrderItemCertification({
    path: path(),
  })
  const data = onResponse(res)
  if (data?.data) {
    item.value = data.data
  }
}
</script>
