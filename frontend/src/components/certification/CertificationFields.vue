<template>
  <div class="flex flex-col gap-3" data-test="certification-fields">
    <q-btn-toggle
      v-model="draft.mode"
      unelevated
      no-caps
      toggle-color="primary"
      :options="[
        { label: 'Nový certifikát', value: 'new' },
        { label: 'Existující', value: 'existing' },
      ]"
    />

    <template v-if="draft.mode === 'new'">
      <q-input
        v-model="draft.code"
        outlined
        dense
        label="Kód certifikátu"
        :rules="requiredRules"
        hide-bottom-space
      />
      <q-input v-model="draft.description" outlined dense label="Popis" type="textarea" autogrow />
      <q-file
        v-model="draft.file"
        outlined
        dense
        label="Příloha (PDF)"
        accept=".pdf,image/*"
        :rules="requiredRules"
        hide-bottom-space
      >
        <template #prepend><q-icon name="sym_o_attach_file" /></template>
      </q-file>
    </template>

    <q-select
      v-else
      v-model="draft.existing"
      outlined
      dense
      label="Certifikát"
      :options="existingOptions"
      option-value="id"
      :option-label="(opt: CertificationSchema) => opt.code"
      use-input
      input-debounce="300"
      :rules="requiredRules"
      hide-bottom-space
      @filter="filterExisting"
    />
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCertificationsGetCertifications,
  type CertificationSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import { computed, ref } from 'vue'
import type { CertificationDraft } from './certification-upload'

const props = defineProps<{
  /** The certificate may be left incomplete (and supplied later). */
  optional?: boolean
}>()

const draft = defineModel<CertificationDraft>('draft', { required: true })

const { onResponse } = useApi()

const requiredRules = computed(() => (props.optional ? [] : [rules.notEmpty]))

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
</script>
