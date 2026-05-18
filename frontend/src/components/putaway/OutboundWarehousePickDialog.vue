<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-3xl max-w-[92vw]">
      <div class="p-4 flex flex-col gap-4">
        <!-- Header -->
        <div class="flex items-start gap-2">
          <div class="flex flex-col gap-1">
            <span class="text-2xl uppercase">Vychystat položku</span>
            <span class="text-gray-5 text-sm">{{ item.product.name }}</span>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <!-- Requirement badges -->
        <div class="flex flex-wrap gap-2 items-center">
          <PackageTypeBadge
            v-if="item.desired_package_type_name"
            :package-type="item.desired_package_type_name"
          />
          <BatchBadge v-if="item.desired_batch_code" :batch-code="item.desired_batch_code" />
        </div>

        <!-- STEP 1: Location Suggestions -->
        <template v-if="currentStep === 'suggest'">
          <!-- Needed amount display -->
          <div class="bg-primary-1 p-4 rounded-xl mb-3">
            <div class="text-sm text-gray-6 mb-1">Potřebné množství pro</div>
            <div class="font-semibold text-lg">{{ item.product.name }}</div>
            <div class="flex items-baseline gap-2 mt-2">
              <span class="text-3xl font-bold text-primary">{{ item.amount }}</span>
              <span class="text-lg text-gray-6">{{ item.product.unit }}</span>
            </div>
          </div>

          <div class="text-sm text-gray-5 uppercase tracking-wide">Dostupné lokace</div>
          <q-list bordered separator class="rounded-sm overflow-hidden">
            <q-item v-for="loc in locationGroupsWithAmounts" :key="loc.code">
              <q-item-section avatar>
                <q-icon name="sym_o_shelves" color="primary" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ loc.warehouseName }} / {{ loc.code }}</q-item-label>
                <q-item-label caption>
                  <span
                    :class="{
                      'text-positive font-semibold': loc.totalAmount >= Number(item.amount),
                      'text-warning font-semibold': loc.totalAmount < Number(item.amount),
                    }"
                  >
                    {{ loc.totalAmount }} {{ item.product.unit }}
                  </span>
                  dostupných
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon
                  v-if="loc.totalAmount >= Number(item.amount)"
                  name="check_circle"
                  color="positive"
                  size="sm"
                />
                <q-icon v-else name="warning" color="warning" size="sm" />
              </q-item-section>
            </q-item>

            <q-item v-if="!loadingSuggestions && locationGroupsWithAmounts.length === 0">
              <q-item-section>
                <q-item-label>Žádné dostupné položky.</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>

          <div class="flex justify-end gap-2">
            <q-btn
              unelevated
              color="primary"
              label="Naskenovat kód"
              icon="qr_code_scanner"
              @click="currentStep = 'scan'"
            />
          </div>
        </template>

        <!-- STEP 2: Barcode Scan Input -->
        <template v-else-if="currentStep === 'scan'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="resetToSuggestions" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Naskenujte kód</span>
          </div>

          <div class="flex flex-col justify-center items-center gap-3 py-4">
            <q-icon name="qr_code_scanner" size="64px" color="primary" />
            <q-input
              v-model="scannedBarcode"
              autofocus
              no-error-icon
              input-class="text-center text-xl"
              inputmode="none"
              class="w-full max-w-xs"
              placeholder="naskenujte položku…"
              @update:model-value="onBarcodeInput"
            />
            <span v-if="lookupError" class="text-negative text-sm">{{ lookupError }}</span>
          </div>

          <q-inner-loading :showing="lookupLoading" />
        </template>

        <!-- STEP 3a: Serialized Item Confirmed -->
        <template v-else-if="currentStep === 'confirm-serialized'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="currentStep = 'scan'" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Položka nalezena</span>
          </div>

          <div class="flex flex-col gap-3">
            <div class="bg-positive-1 p-4 rounded-xl flex items-center gap-3">
              <q-icon name="check_circle" color="positive" size="48px" />
              <div class="flex flex-col gap-1">
                <span class="text-lg font-semibold">{{
                  lookupResult?.warehouse_item?.product.name
                }}</span>
                <span class="text-sm text-gray-6">
                  Lokace: {{ lookupResult?.warehouse_item?.location.code }}
                </span>
                <div class="flex gap-2 flex-wrap">
                  <WarehouseItemAmountBadge
                    v-if="lookupResult?.warehouse_item"
                    :item="lookupResult.warehouse_item"
                  />
                  <WarehouseItemTypeBadgeGroup
                    v-if="lookupResult?.warehouse_item"
                    :item="lookupResult.warehouse_item"
                  />
                </div>
              </div>
            </div>

            <!-- Partial pick option for packages -->
            <div v-if="canPickPartial" class="flex flex-col gap-3">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Množství</div>
              <q-btn-toggle
                v-model="partialPick"
                :options="[
                  { label: 'Celý balík', value: false },
                  { label: 'Částečně', value: true },
                ]"
                unelevated
                toggle-color="primary"
              />

              <!-- Visual Amount Comparison when partial picking -->
              <div v-if="partialPick" class="bg-white border-2 border-gray-3 rounded-xl p-4 flex flex-col gap-3">
                <div class="flex justify-between items-center">
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-gray-5 uppercase tracking-wide">Potřebné množství</span>
                    <div class="flex items-baseline gap-1">
                      <span class="text-3xl font-bold text-primary">{{ item.amount }}</span>
                      <span class="text-lg text-gray-6">{{
                        lookupResult?.warehouse_item?.unit_of_measure
                      }}</span>
                    </div>
                  </div>
                  <q-icon name="arrow_forward" color="gray-5" size="32px" />
                  <div class="flex flex-col gap-1 items-end">
                    <span class="text-xs text-gray-5 uppercase tracking-wide">V balíku</span>
                    <div class="flex items-baseline gap-1">
                      <span class="text-3xl font-bold text-positive">{{
                        lookupResult?.warehouse_item?.amount
                      }}</span>
                      <span class="text-lg text-gray-6">{{
                        lookupResult?.warehouse_item?.unit_of_measure
                      }}</span>
                    </div>
                  </div>
                </div>

                <q-input
                  v-model.number="pickAmount"
                  type="number"
                  step="0.01"
                  label="Množství k vychystání"
                  :rules="[
                    (val) => val > 0 || 'Množství musí být kladné',
                    (val) =>
                      val <= (lookupResult?.warehouse_item?.amount ?? 0) ||
                      'Překročeno dostupné množství',
                  ]"
                  outlined
                  dense
                >
                  <template #append>
                    <span class="text-gray-5">{{
                      lookupResult?.warehouse_item?.unit_of_measure
                    }}</span>
                  </template>
                </q-input>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <q-btn flat label="zpět" @click="currentStep = 'scan'" />
            <q-btn
              unelevated
              color="primary"
              label="potvrdit výběr"
              :disable="partialPick && !isSerializedPickAmountValid"
              :loading="assigning"
              @click="confirmSerializedPick"
            />
          </div>
        </template>

        <!-- STEP 3b: Scan Location for Product/Batch -->
        <template v-else-if="currentStep === 'scan-location-for-product'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="currentStep = 'scan'" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Vyberte lokaci</span>
          </div>

          <div class="flex flex-col gap-3">
            <!-- Product/Batch Info with needed amount -->
            <div class="bg-blue-1 p-4 rounded-xl">
              <div class="font-semibold">
                {{ lookupResult?.batch?.description ?? lookupResult?.product?.name ?? 'Položka' }}
              </div>
              <div class="flex items-center gap-3 mt-2">
                <div class="flex flex-col">
                  <span class="text-xs text-gray-6">Potřebné množství</span>
                  <span class="text-lg font-bold text-primary">
                    {{ item.amount }} {{ lookupResult?.matching_items?.[0]?.unit_of_measure ?? '' }}
                  </span>
                </div>
                <q-separator vertical />
                <div class="flex flex-col">
                  <span class="text-xs text-gray-6">Celkem dostupné</span>
                  <span class="text-lg font-bold">
                    {{
                      (lookupResult?.matching_items ?? []).reduce((sum, item) => sum + item.amount, 0)
                    }}
                    {{ lookupResult?.matching_items?.[0]?.unit_of_measure ?? '' }}
                  </span>
                </div>
              </div>
            </div>

            <div class="flex flex-col justify-center items-center gap-3 py-4">
              <q-icon name="sym_o_shelves" size="48px" color="primary" />
              <span class="text-sm text-gray-5 uppercase">Zadejte kód lokace</span>
              <q-input
                v-model="scannedBarcode"
                autofocus
                no-error-icon
                input-class="text-center text-lg uppercase"
                class="w-full max-w-xs"
                placeholder="např. A1-01-03…"
                @update:model-value="onLocationScanForProduct"
              />
            </div>

            <!-- Show available locations with amounts -->
            <div v-if="fungibleLocations.length > 0" class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">
                Dostupné lokace ({{ fungibleLocations.length }}) - klikněte pro výběr
              </div>
              <q-list bordered separator class="rounded-xl overflow-hidden max-h-64 overflow-y-auto">
                <q-item
                  v-for="loc in fungibleLocations"
                  :key="loc.code"
                  clickable
                  @click="
                    () => {
                      selectedLocation = loc.code
                      currentStep = 'pick-fungible'
                      pickAmount = Number(item.amount)
                      scannedBarcode = ''
                    }
                  "
                >
                  <q-item-section avatar>
                    <q-icon name="sym_o_shelves" color="primary" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ loc.warehouseName }} / {{ loc.code }}</q-item-label>
                    <q-item-label caption>
                      <span
                        :class="{
                          'text-positive font-semibold': loc.totalAmount >= Number(item.amount),
                          'text-warning font-semibold': loc.totalAmount < Number(item.amount),
                        }"
                      >
                        {{ loc.totalAmount }} {{ loc.unit }}
                      </span>
                      dostupných
                    </q-item-label>
                  </q-item-section>
                  <q-item-section side>
                    <q-icon
                      v-if="loc.totalAmount >= Number(item.amount)"
                      name="check_circle"
                      color="positive"
                      size="sm"
                    />
                    <q-icon v-else name="warning" color="warning" size="sm" />
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <q-btn flat label="zpět" @click="currentStep = 'scan'" />
          </div>
        </template>

        <!-- STEP 3c: Fungible/Batch - Location and Amount Selection -->
        <template v-else-if="currentStep === 'pick-fungible'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="currentStep = 'scan'" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Množství k vychystání</span>
          </div>

          <div class="flex flex-col gap-3">
            <!-- Product/Batch Info -->
            <div class="bg-blue-1 p-4 rounded-xl">
              <div class="font-semibold">
                {{ lookupResult?.batch?.description ?? lookupResult?.product?.name ?? props.item.product.name }}
              </div>
              <div class="text-sm text-gray-6">
                Lokace: {{ selectedLocation }}
              </div>
            </div>

            <!-- Visual Amount Comparison -->
            <div class="bg-white border-2 border-gray-3 rounded-xl p-4 flex flex-col gap-3">
              <div class="flex justify-between items-center">
                <div class="flex flex-col gap-1">
                  <span class="text-xs text-gray-5 uppercase tracking-wide">Potřebné množství</span>
                  <div class="flex items-baseline gap-1">
                    <span class="text-3xl font-bold text-primary">{{ item.amount }}</span>
                    <span class="text-lg text-gray-6">{{ unitOfMeasure }}</span>
                  </div>
                </div>
                <q-icon
                  :name="maxAvailableInLocation >= Number(item.amount) ? 'check_circle' : 'warning'"
                  :color="maxAvailableInLocation >= Number(item.amount) ? 'positive' : 'warning'"
                  size="48px"
                />
                <div class="flex flex-col gap-1 items-end">
                  <span class="text-xs text-gray-5 uppercase tracking-wide">Dostupné na lokaci</span>
                  <div class="flex items-baseline gap-1">
                    <span
                      class="text-3xl font-bold"
                      :class="{
                        'text-positive': maxAvailableInLocation >= Number(item.amount),
                        'text-warning': maxAvailableInLocation < Number(item.amount),
                      }"
                    >
                      {{ maxAvailableInLocation }}
                    </span>
                    <span class="text-lg text-gray-6">{{ unitOfMeasure }}</span>
                  </div>
                </div>
              </div>

              <!-- Visual bar comparison -->
              <div class="flex flex-col gap-1">
                <div class="flex gap-2 items-center">
                  <div class="flex-1 h-3 bg-gray-2 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-primary rounded-full transition-all"
                      :style="{
                        width: `${Math.min((Number(item.amount) / Math.max(maxAvailableInLocation, Number(item.amount))) * 100, 100)}%`,
                      }"
                    />
                  </div>
                  <span class="text-xs text-gray-5 min-w-[60px]">Potřebné</span>
                </div>
                <div class="flex gap-2 items-center">
                  <div class="flex-1 h-3 bg-gray-2 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all"
                      :class="{
                        'bg-positive': maxAvailableInLocation >= Number(item.amount),
                        'bg-warning': maxAvailableInLocation < Number(item.amount),
                      }"
                      :style="{
                        width: `${Math.min((maxAvailableInLocation / Math.max(maxAvailableInLocation, Number(item.amount))) * 100, 100)}%`,
                      }"
                    />
                  </div>
                  <span class="text-xs text-gray-5 min-w-[60px]">Dostupné</span>
                </div>
              </div>

              <!-- Status message -->
              <div
                v-if="maxAvailableInLocation < Number(item.amount)"
                class="flex items-center gap-2 p-2 bg-warning-1 rounded-lg"
              >
                <q-icon name="info" color="warning" size="sm" />
                <span class="text-sm text-warning-8">
                  Částečné splnění: chybí {{ Number(item.amount) - maxAvailableInLocation }}
                  {{ unitOfMeasure }}
                </span>
              </div>
              <div
                v-else-if="maxAvailableInLocation > Number(item.amount)"
                class="flex items-center gap-2 p-2 bg-positive-1 rounded-lg"
              >
                <q-icon name="check" color="positive" size="sm" />
                <span class="text-sm text-positive-8">
                  Přebytek: {{ maxAvailableInLocation - Number(item.amount) }} {{ unitOfMeasure }}
                  zůstane na lokaci
                </span>
              </div>
            </div>

            <!-- Amount input -->
            <div class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Množství k vychystání</div>
              <q-input
                v-model.number="pickAmount"
                type="number"
                step="0.01"
                :rules="[
                  (val) => val > 0 || 'Množství musí být kladné',
                  (val) => val <= maxAvailableInLocation || `Max: ${maxAvailableInLocation}`,
                ]"
                outlined
                dense
                autofocus
              >
                <template #append>
                  <span class="text-gray-5">{{ unitOfMeasure }}</span>
                </template>
              </q-input>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <q-btn
              flat
              label="zpět"
              @click="
                currentStep =
                  lookupResult?.entity_type === 'warehouse_item' ? 'scan' : 'scan-location-for-product'
              "
            />
            <q-btn
              unelevated
              color="primary"
              label="potvrdit výběr"
              :disable="!selectedLocation || !isPickAmountValid"
              :loading="assigning"
              @click="confirmFungiblePick"
            />
          </div>
        </template>

        <!-- STEP 3d: Location Scan Fallback -->
        <template v-else-if="currentStep === 'confirm-location'">
          <div class="flex items-center gap-2">
            <q-btn flat round dense icon="arrow_back" @click="currentStep = 'scan'" />
            <span class="text-sm uppercase tracking-wide text-gray-5">Lokace nalezena</span>
          </div>

          <div class="flex flex-col gap-3">
            <div class="bg-blue-1 p-4 rounded-xl">
              <div class="font-semibold">
                {{ lookupResult?.location?.warehouse_name }} / {{ lookupResult?.location?.code }}
              </div>
              <div class="text-sm text-gray-6">
                {{ props.item.product.name }}
              </div>
            </div>

            <!-- Item selection for serialized items -->
            <div v-if="hasSerializedItems" class="flex flex-col gap-2">
              <div class="text-sm text-gray-5 uppercase tracking-wide">Vyberte položku</div>
              <q-list bordered separator class="rounded-xl overflow-hidden">
                <q-item
                  v-for="matchedItem in lookupResult?.matching_items"
                  :key="matchedItem.id"
                  clickable
                  :active="selectedWarehouseItemId === matchedItem.id"
                  @click="selectedWarehouseItemId = matchedItem.id"
                >
                  <q-item-section avatar>
                    <q-radio v-model="selectedWarehouseItemId" :val="matchedItem.id" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ matchedItem.product.name }}</q-item-label>
                  </q-item-section>
                  <q-item-section side class="items-end gap-2">
                    <WarehouseItemAmountBadge :item="matchedItem" />
                    <WarehouseItemTypeBadgeGroup :item="matchedItem" />
                  </q-item-section>
                </q-item>
              </q-list>
            </div>

            <!-- Amount input for fungible items with visual comparison -->
            <div v-else class="flex flex-col gap-3">
              <!-- Visual Amount Comparison -->
              <div class="bg-white border-2 border-gray-3 rounded-xl p-4 flex flex-col gap-3">
                <div class="flex justify-between items-center">
                  <div class="flex flex-col gap-1">
                    <span class="text-xs text-gray-5 uppercase tracking-wide">Potřebné množství</span>
                    <div class="flex items-baseline gap-1">
                      <span class="text-3xl font-bold text-primary">{{ item.amount }}</span>
                      <span class="text-lg text-gray-6">{{ unitOfMeasure }}</span>
                    </div>
                  </div>
                  <q-icon
                    :name="maxAvailableInLocation >= Number(item.amount) ? 'check_circle' : 'warning'"
                    :color="maxAvailableInLocation >= Number(item.amount) ? 'positive' : 'warning'"
                    size="48px"
                  />
                  <div class="flex flex-col gap-1 items-end">
                    <span class="text-xs text-gray-5 uppercase tracking-wide">Dostupné na lokaci</span>
                    <div class="flex items-baseline gap-1">
                      <span
                        class="text-3xl font-bold"
                        :class="{
                          'text-positive': maxAvailableInLocation >= Number(item.amount),
                          'text-warning': maxAvailableInLocation < Number(item.amount),
                        }"
                      >
                        {{ maxAvailableInLocation }}
                      </span>
                      <span class="text-lg text-gray-6">{{ unitOfMeasure }}</span>
                    </div>
                  </div>
                </div>

                <!-- Visual bar comparison -->
                <div class="flex flex-col gap-1">
                  <div class="flex gap-2 items-center">
                    <div class="flex-1 h-3 bg-gray-2 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-primary rounded-full transition-all"
                        :style="{
                          width: `${Math.min((Number(item.amount) / Math.max(maxAvailableInLocation, Number(item.amount))) * 100, 100)}%`,
                        }"
                      />
                    </div>
                    <span class="text-xs text-gray-5 min-w-[60px]">Potřebné</span>
                  </div>
                  <div class="flex gap-2 items-center">
                    <div class="flex-1 h-3 bg-gray-2 rounded-full overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all"
                        :class="{
                          'bg-positive': maxAvailableInLocation >= Number(item.amount),
                          'bg-warning': maxAvailableInLocation < Number(item.amount),
                        }"
                        :style="{
                          width: `${Math.min((maxAvailableInLocation / Math.max(maxAvailableInLocation, Number(item.amount))) * 100, 100)}%`,
                        }"
                      />
                    </div>
                    <span class="text-xs text-gray-5 min-w-[60px]">Dostupné</span>
                  </div>
                </div>

                <!-- Status message -->
                <div
                  v-if="maxAvailableInLocation < Number(item.amount)"
                  class="flex items-center gap-2 p-2 bg-warning-1 rounded-lg"
                >
                  <q-icon name="info" color="warning" size="sm" />
                  <span class="text-sm text-warning-8">
                    Částečné splnění: chybí {{ Number(item.amount) - maxAvailableInLocation }}
                    {{ unitOfMeasure }}
                  </span>
                </div>
                <div
                  v-else-if="maxAvailableInLocation > Number(item.amount)"
                  class="flex items-center gap-2 p-2 bg-positive-1 rounded-lg"
                >
                  <q-icon name="check" color="positive" size="sm" />
                  <span class="text-sm text-positive-8">
                    Přebytek: {{ maxAvailableInLocation - Number(item.amount) }} {{ unitOfMeasure }}
                    zůstane na lokaci
                  </span>
                </div>
              </div>

              <div class="text-sm text-gray-5 uppercase tracking-wide">Množství k vychystání</div>
              <q-input
                v-model.number="pickAmount"
                type="number"
                step="0.01"
                :rules="[
                  (val) => val > 0 || 'Množství musí být kladné',
                  (val) => val <= maxAvailableInLocation || `Max: ${maxAvailableInLocation}`,
                ]"
                outlined
                dense
                autofocus
              >
                <template #append>
                  <span class="text-gray-5">{{ unitOfMeasure }}</span>
                </template>
              </q-input>
            </div>
          </div>

          <div class="flex justify-end gap-2">
            <q-btn flat label="zpět" @click="currentStep = 'scan'" />
            <q-btn
              unelevated
              color="primary"
              label="potvrdit výběr"
              :disable="hasSerializedItems ? !selectedWarehouseItemId : !isPickAmountValid"
              :loading="assigning"
              @click="confirmLocationPick"
            />
          </div>
        </template>

        <q-inner-loading :showing="loadingSuggestions" />
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  type OutboundWarehouseOrderItemSchema,
  type WarehouseItemSchema,
  type BarcodeLookupResponse,
  warehouseApiRoutesProductGetProductWarehouseInfo,
  warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useAppSettings } from '@/composables/use-app-settings'
import { useBarcodeLookup } from '@/composables/use-barcode-lookup'
import { computed, ref, watch } from 'vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import WarehouseItemAmountBadge from '../warehouse/WarehouseItemAmountBadge.vue'
import WarehouseItemTypeBadgeGroup from '../warehouse/WarehouseItemTypeBadgeGroup.vue'

type Step =
  | 'suggest'
  | 'scan'
  | 'confirm-serialized'
  | 'pick-fungible'
  | 'confirm-location'
  | 'scan-location-for-product'

const props = defineProps<{
  warehouseOrderCode: string
  item: OutboundWarehouseOrderItemSchema
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
}>()

const showDialog = defineModel<boolean>('show', { default: false })
const { onResponse } = useApi()
const { scannerMode } = useAppSettings()
const { lookup, loading: lookupLoading, error: lookupError } = useBarcodeLookup()

// State
const currentStep = ref<Step>('suggest')
const scannedBarcode = ref('')
const lookupResult = ref<BarcodeLookupResponse | null>(null)
const selectedWarehouseItemId = ref<number | null>(null)
const selectedLocation = ref<string | null>(null)
const pickAmount = ref<number>(0)
const partialPick = ref(false)
const loadingSuggestions = ref(false)
const allCandidates = ref<WarehouseItemSchema[]>([])
const assigning = ref(false)

// Computed - Location suggestions
type LocationGroupWithAmount = { code: string; warehouseName: string; count: number; totalAmount: number }

const locationGroupsWithAmounts = computed<LocationGroupWithAmount[]>(() => {
  const map = new Map<string, LocationGroupWithAmount>()
  for (const c of allCandidates.value) {
    const key = c.location.code
    if (map.has(key)) {
      const group = map.get(key)!
      group.count++
      group.totalAmount += c.amount
    } else {
      map.set(key, {
        code: key,
        warehouseName: c.location.warehouse_name,
        count: 1,
        totalAmount: c.amount,
      })
    }
  }
  return Array.from(map.values()).sort((a, b) => b.totalAmount - a.totalAmount)
})

// Computed - Serialized item partial pick
const canPickPartial = computed(() => {
  const item = lookupResult.value?.warehouse_item
  if (!item) return false
  const isSerialized =
    item.tracking_level === 'SERIALIZED_PACKAGE' || item.tracking_level === 'SERIALIZED_PIECE'
  // Allow partial pick if serialized and amount is greater than requested OR amount > 0 (to support decimals)
  return isSerialized && item.amount > 0
})

// Computed - Fungible location groups
type FungibleLocation = {
  code: string
  warehouseName: string
  totalAmount: number
  unit: string
}

const fungibleLocations = computed<FungibleLocation[]>(() => {
  const items = lookupResult.value?.matching_items ?? []
  const map = new Map<string, FungibleLocation>()

  for (const item of items) {
    const key = item.location.code
    if (map.has(key)) {
      map.get(key)!.totalAmount += item.amount
    } else {
      map.set(key, {
        code: key,
        warehouseName: item.location.warehouse_name,
        totalAmount: item.amount,
        unit: item.unit_of_measure,
      })
    }
  }

  return Array.from(map.values())
})

const maxAvailableInLocation = computed(() => {
  if (!selectedLocation.value) return 0
  const loc = fungibleLocations.value.find((l) => l.code === selectedLocation.value)
  return loc?.totalAmount ?? 0
})

const unitOfMeasure = computed(() => {
  const items = lookupResult.value?.matching_items ?? []
  return items[0]?.unit_of_measure ?? ''
})

const hasSerializedItems = computed(() => {
  const items = lookupResult.value?.matching_items ?? []
  return items.some(
    (item) =>
      item.tracking_level === 'SERIALIZED_PACKAGE' || item.tracking_level === 'SERIALIZED_PIECE',
  )
})

// Validation computed
const isPickAmountValid = computed(() => {
  return pickAmount.value > 0 && pickAmount.value <= maxAvailableInLocation.value
})

const isSerializedPickAmountValid = computed(() => {
  const maxAvailable = lookupResult.value?.warehouse_item?.amount ?? 0
  return pickAmount.value > 0 && pickAmount.value <= maxAvailable
})

// Actions
const loadSuggestions = async () => {
  loadingSuggestions.value = true
  const response = await warehouseApiRoutesProductGetProductWarehouseInfo({
    path: { product_code: props.item.product.code },
    query: {
      package_type_name: props.item.desired_package_type_name ?? undefined,
      batch_code: props.item.desired_batch_code ?? undefined,
    },
  })
  const data = onResponse(response)
  allCandidates.value = (data?.data ?? []).flatMap((wh) => wh.locations.flatMap((loc) => loc.items))
  loadingSuggestions.value = false
}

const resetToSuggestions = () => {
  currentStep.value = 'suggest'
  scannedBarcode.value = ''
  lookupResult.value = null
  selectedWarehouseItemId.value = null
  selectedLocation.value = null
  pickAmount.value = 0
  partialPick.value = false
}

const onBarcodeInput = async (barcode: string | number | null) => {
  if (!barcode || typeof barcode !== 'string' || barcode.length < 3) return

  const result = await lookup(barcode, props.item.product.code)
  if (!result || !result.found) {
    return
  }

  lookupResult.value = result

  // Route to appropriate step based on entity type
  if (result.entity_type === 'warehouse_item') {
    const item = result.warehouse_item
    if (!item) return

    // For warehouse item scans, we know the item and location already
    // But still show confirmation step
    if (
      item.tracking_level === 'SERIALIZED_PACKAGE' ||
      item.tracking_level === 'SERIALIZED_PIECE'
    ) {
      currentStep.value = 'confirm-serialized'
      selectedLocation.value = item.location.code
      pickAmount.value = item.amount

      // Auto-confirm in scanner mode after delay
      if (scannerMode.value && !canPickPartial.value) {
        setTimeout(() => {
          void confirmSerializedPick()
        }, 400)
      }
    } else {
      // Fungible/batch item - need location confirmation and amount
      selectedLocation.value = item.location.code
      currentStep.value = 'pick-fungible'
      pickAmount.value = Number(props.item.amount)
    }
  } else if (result.entity_type === 'batch' || result.entity_type === 'product') {
    // ALWAYS ask for location scan, never auto-select
    currentStep.value = 'scan-location-for-product'
    scannedBarcode.value = ''
  } else if (result.entity_type === 'location') {
    // Location scanned but we need to know which product
    currentStep.value = 'confirm-location'
    selectedLocation.value = result.location?.code ?? null
    pickAmount.value = Number(props.item.amount)
    // Auto-select first item if only one
    if (result.matching_items?.length === 1) {
      selectedWarehouseItemId.value = result.matching_items[0].id
    }
  }
}

const onLocationScanForProduct = async (locationCode: string | number | null) => {
  if (!locationCode || typeof locationCode !== 'string' || locationCode.length < 1) return

  lookupError.value = null

  // Search for location by code in the available locations
  const matchingLocation = fungibleLocations.value.find(
    (loc) => loc.code.toLowerCase() === locationCode.trim().toLowerCase()
  )

  if (!matchingLocation) {
    // Location code not found in available locations
    return
  }

  // Filter matching items to only those in this location
  const itemsInLocation =
    lookupResult.value?.matching_items?.filter(
      (item) => item.location.code.toLowerCase() === locationCode.trim().toLowerCase()
    ) ?? []

  if (itemsInLocation.length === 0) {
    return
  }

  // Set the selected location and proceed to amount input
  selectedLocation.value = matchingLocation.code
  currentStep.value = 'pick-fungible'
  pickAmount.value = Number(props.item.amount)
  scannedBarcode.value = ''
}

const confirmSerializedPick = async () => {
  const warehouseItemId = lookupResult.value?.warehouse_item?.id
  if (!warehouseItemId) return

  // Validate amount if partial picking
  if (partialPick.value && !isSerializedPickAmountValid.value) {
    return
  }

  // Double-check amount doesn't exceed available
  if (partialPick.value && pickAmount.value > (lookupResult.value?.warehouse_item?.amount ?? 0)) {
    return
  }

  assigning.value = true
  try {
    const amount = partialPick.value ? pickAmount.value : null
    const response = await warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem({
      path: {
        code: props.warehouseOrderCode,
        item_id: props.item.id,
      },
      body: {
        warehouse_item_id: warehouseItemId,
        amount: amount !== null ? String(amount) : null,
      },
    })
    const result = onResponse(response)
    if (result) {
      emit('confirm')
      showDialog.value = false
    }
  } finally {
    assigning.value = false
  }
}

const confirmFungiblePick = async () => {
  if (!selectedLocation.value) return

  // Validate amount before proceeding
  if (!isPickAmountValid.value) {
    return
  }

  // Find first warehouse item in the selected location
  const items = lookupResult.value?.matching_items ?? []
  const itemInLocation = items.find((item) => item.location.code === selectedLocation.value)
  if (!itemInLocation) return

  // Double-check amount doesn't exceed available
  if (pickAmount.value > itemInLocation.amount) {
    return
  }

  assigning.value = true
  try {
    const response = await warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem({
      path: {
        code: props.warehouseOrderCode,
        item_id: props.item.id,
      },
      body: {
        warehouse_item_id: itemInLocation.id,
        amount: String(pickAmount.value),
      },
    })
    onResponse(response)
    emit('confirm')
    showDialog.value = false
  } finally {
    assigning.value = false
  }
}

const confirmLocationPick = async () => {
  let warehouseItemId: number

  if (hasSerializedItems.value) {
    if (!selectedWarehouseItemId.value) return
    warehouseItemId = selectedWarehouseItemId.value
  } else {
    // Validate amount for fungible items
    if (!isPickAmountValid.value) {
      return
    }

    // Fungible - use first item in location
    const items = lookupResult.value?.matching_items ?? []
    const itemInLocation = items[0]
    if (!itemInLocation) return

    // Double-check amount doesn't exceed available
    if (pickAmount.value > maxAvailableInLocation.value) {
      return
    }

    warehouseItemId = itemInLocation.id
  }

  assigning.value = true
  try {
    const response = await warehouseApiRoutesWarehouseAssignOutboundWarehouseOrderItem({
      path: {
        code: props.warehouseOrderCode,
        item_id: props.item.id,
      },
      body: {
        warehouse_item_id: warehouseItemId,
        amount: hasSerializedItems.value ? null : String(pickAmount.value),
      },
    })
    const result = onResponse(response)
    if (result) {
      emit('confirm')
      showDialog.value = false
    }
  } finally {
    assigning.value = false
  }
}

// Watchers
watch(
  () => showDialog.value,
  (opened) => {
    if (opened) {
      resetToSuggestions()
      void loadSuggestions()
    }
  },
)

// Removed auto-select logic - always require manual location selection/scan

// Clear lookup error when user types
watch(scannedBarcode, () => {
  if (lookupError.value) {
    lookupError.value = null
  }
})
</script>
