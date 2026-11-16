<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col gap-4">
        <div class="flex items-start gap-2">
          <div class="flex flex-col">
            <span class="text-2xl uppercase">Požadavek na výdej</span>
            <span class="text-gray-5 text-sm">{{ productName }}</span>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="submit">
          <div
            v-if="!active.length"
            class="text-sm text-muted text-center py-4"
            data-test="no-requirements"
          >
            Bez požadavků - lze vybrat libovolné zboží.
          </div>

          <div
            v-for="type in active"
            :key="type"
            class="flex flex-col gap-2 p-3 rounded border border-solid light:border-slate-200 dark:border-gray-7"
            :data-test="`requirement-${type}`"
          >
            <div class="flex items-center gap-2">
              <q-icon :name="typeMeta[type].icon" color="primary" />
              <span class="font-medium">{{ typeMeta[type].label }}</span>
              <q-btn
                flat
                round
                dense
                icon="sym_o_close"
                class="ml-auto"
                :data-test="`remove-${type}`"
                @click="remove(type)"
              />
            </div>

            <PackageTypeSearchSelect v-if="type === 'package'" v-model="selectedPackage" />

            <q-input
              v-else-if="type === 'batch'"
              v-model.trim="batchCode"
              outlined
              label="Kód šarže"
              :rules="[rules.notEmpty]"
            />

            <CertifiedStockPicker
              v-else-if="type === 'certification'"
              v-model="certifiedBatchCode"
              :product-code="productCode"
            />

            <CountrySelect
              v-else
              v-model="country"
              hint="Zboží musí pocházet z vybrané země"
              :rules="[rules.notEmpty]"
            />
          </div>

          <q-btn-dropdown
            v-if="available.length"
            flat
            no-caps
            color="primary"
            icon="sym_o_add"
            label="přidat požadavek"
            class="self-start"
            data-test="add-requirement"
          >
            <q-list dense>
              <q-item
                v-for="type in available"
                :key="type"
                v-close-popup
                clickable
                :data-test="`add-${type}`"
                @click="add(type)"
              >
                <q-item-section avatar><q-icon :name="typeMeta[type].icon" /></q-item-section>
                <q-item-section>{{ typeMeta[type].label }}</q-item-section>
              </q-item>
            </q-list>
          </q-btn-dropdown>

          <div class="flex gap-2 justify-end pt-2">
            <q-btn flat color="negative" label="vymazat vše" @click="clearRequirements" />
            <q-btn
              unelevated
              color="primary"
              label="uložit"
              type="submit"
              :disable="!canSave"
              data-test="save-requirements"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { PackageTypeSchema } from '@/client'
import { rules } from '@/utils/rules'
import { computed, ref, watch } from 'vue'
import CertifiedStockPicker from '../certification/CertifiedStockPicker.vue'
import CountrySelect from '../selects/CountrySelect.vue'
import PackageTypeSearchSelect from '../selects/PackageTypeSearchSelect.vue'

type RequirementType = 'package' | 'batch' | 'certification' | 'country'

const props = defineProps<{
  productName: string
  productCode: string
  /** requirement row to start with when nothing is set yet */
  initialMode?: Exclude<RequirementType, 'country'>
  desiredPackageTypeName?: string | null
  desiredBatchCode?: string | null
  requiredOriginCountry?: string | null
}>()

const emit = defineEmits<{
  (
    e: 'save',
    payload: {
      desired_package_type_name: string | null
      desired_batch_code: string | null
      required_origin_country: string | null
    },
  ): void
}>()

const showDialog = defineModel<boolean>('show', { default: false })

const typeMeta: Record<RequirementType, { label: string; icon: string }> = {
  package: { label: 'Typ balení', icon: 'sym_o_package_2' },
  batch: { label: 'Šarže', icon: 'sym_o_barcode' },
  certification: { label: 'Certifikace', icon: 'sym_o_verified' },
  country: { label: 'Země původu', icon: 'sym_o_public' },
}

// a requirement can be given once; a certification resolves to a batch, so it
// excludes (and is excluded by) an explicit batch
const EXCLUDES: Partial<Record<RequirementType, RequirementType>> = {
  batch: 'certification',
  certification: 'batch',
}

const active = ref<RequirementType[]>([])
const selectedPackage = ref<PackageTypeSchema>()
const batchCode = ref('')
const certifiedBatchCode = ref<string | null>(null)
const country = ref<string | null>(null)

const available = computed(() =>
  (Object.keys(typeMeta) as RequirementType[]).filter(
    (type) =>
      !active.value.includes(type) && !(EXCLUDES[type] && active.value.includes(EXCLUDES[type])),
  ),
)

// rows whose value can not be validated by the form itself
const canSave = computed(
  () => !active.value.includes('certification') || !!certifiedBatchCode.value,
)

const add = (type: RequirementType) => {
  if (available.value.includes(type)) active.value.push(type)
}

const remove = (type: RequirementType) => {
  active.value = active.value.filter((t) => t !== type)
}

watch(
  () => showDialog.value,
  (opened) => {
    if (!opened) {
      return
    }
    batchCode.value = props.desiredBatchCode ?? ''
    certifiedBatchCode.value = null
    country.value = props.requiredOriginCountry ?? null
    selectedPackage.value = props.desiredPackageTypeName
      ? ({ name: props.desiredPackageTypeName } as PackageTypeSchema)
      : undefined

    const rows: RequirementType[] = []
    if (props.desiredPackageTypeName) rows.push('package')
    if (props.desiredBatchCode) rows.push('batch')
    if (props.requiredOriginCountry) rows.push('country')
    if (!rows.length && props.initialMode) rows.push(props.initialMode)
    active.value = rows
  },
)

const has = (type: RequirementType) => active.value.includes(type)

const submit = () => {
  emit('save', {
    desired_package_type_name: has('package') ? (selectedPackage.value?.name ?? null) : null,
    // a certification resolves to one of its batches - stored as a plain batch requirement
    desired_batch_code: has('batch')
      ? batchCode.value || null
      : has('certification')
        ? certifiedBatchCode.value
        : null,
    required_origin_country: has('country') ? country.value || null : null,
  })
  showDialog.value = false
}

const clearRequirements = () => {
  active.value = []
  submit()
}
</script>
