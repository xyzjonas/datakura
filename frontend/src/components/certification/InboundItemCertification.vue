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

      <q-btn-toggle
        v-model="mode"
        unelevated
        no-caps
        toggle-color="primary"
        :options="[
          { label: 'Nový certifikát', value: 'new' },
          { label: 'Existující', value: 'existing' },
        ]"
      />

      <template v-if="mode === 'new'">
        <q-input
          v-model="code"
          outlined
          dense
          label="Kód certifikátu"
          :rules="[rules.notEmpty]"
          hide-bottom-space
        />
        <q-input v-model="description" outlined dense label="Popis" type="textarea" autogrow />
        <q-file
          v-model="file"
          outlined
          dense
          label="Příloha (PDF)"
          accept=".pdf,image/*"
          :rules="[rules.notEmpty]"
          hide-bottom-space
        >
          <template #prepend><q-icon name="sym_o_attach_file" /></template>
        </q-file>
      </template>

      <q-select
        v-else
        v-model="existing"
        outlined
        dense
        label="Certifikát"
        :options="existingOptions"
        option-value="id"
        :option-label="(opt: CertificationSchema) => opt.code"
        use-input
        input-debounce="300"
        :rules="[rules.notEmpty]"
        hide-bottom-space
        @filter="filterExisting"
      />

      <div class="flex justify-end gap-2">
        <q-btn v-if="item.certification" flat no-caps label="Zrušit" @click="editing = false" />
        <q-btn unelevated no-caps color="primary" label="uložit certifikát" type="submit" />
      </div>
    </q-form>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCertificationsGetCertifications,
  warehouseApiRoutesInboundOrdersRemoveInboundOrderItemCertification,
  warehouseApiRoutesInboundOrdersSetInboundOrderItemCertification,
  type CertificationSchema,
  type InboundOrderItemSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import { ref } from 'vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import CertificationFileLink from './CertificationFileLink.vue'
import { multipartRequestOptions, toCertificationMultipartBody } from './certification-upload'

const { onResponse } = useApi()

const props = defineProps<{ orderCode: string; readonly?: boolean }>()

const item = defineModel<InboundOrderItemSchema>('item', { required: true })

const editing = ref(false)
const mode = ref<'new' | 'existing'>('new')
const code = ref('')
const description = ref('')
const file = ref<File | null>(null)
const existing = ref<CertificationSchema | null>(null)
const existingOptions = ref<CertificationSchema[]>([])

const filterExisting = async (term: string, update: (cb: () => void) => void) => {
  const res = await warehouseApiRoutesCertificationsGetCertifications({
    query: { search_term: term || undefined },
  })
  const data = onResponse(res)
  update(() => {
    existingOptions.value = data?.data ?? []
  })
}

const path = () => ({ order_code: props.orderCode, item_index: item.value.index })

const submit = async () => {
  const fields =
    mode.value === 'new'
      ? { code: code.value, description: description.value }
      : { certification_id: existing.value?.id }
  const res = await warehouseApiRoutesInboundOrdersSetInboundOrderItemCertification({
    path: path(),
    body: toCertificationMultipartBody(fields, mode.value === 'new' ? file.value : null),
    ...multipartRequestOptions,
  })
  const data = onResponse(res)
  if (data?.data) {
    item.value = data.data
    editing.value = false
    code.value = ''
    description.value = ''
    file.value = null
    existing.value = null
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
