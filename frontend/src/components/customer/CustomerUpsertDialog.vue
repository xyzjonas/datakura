<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <!-- Basic Information -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.code" outlined label="Kód" :rules="[rules.notEmpty]" />
            <q-input v-model.trim="form.name" outlined label="Název" :rules="[rules.notEmpty]" />
            <q-select
              v-model="form.customer_type"
              :options="customerTypeOptions"
              option-label="label"
              option-value="value"
              emit-value
              map-options
              outlined
              label="Typ"
              :rules="[rules.notEmpty]"
            />
            <q-select
              v-model="form.price_type"
              :options="priceTypeOptions"
              option-label="label"
              option-value="value"
              emit-value
              map-options
              outlined
              label="Cenový typ"
              :rules="[rules.notEmpty]"
            />
          </div>

          <!-- Tax Information -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.identification" outlined label="IČ" />
            <q-input v-model.trim="form.tax_identification" outlined label="DIČ" />
          </div>

          <!-- Address -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.street" outlined label="Ulice" class="col-span-2" />
            <q-input v-model.trim="form.city" outlined label="Město" />
            <q-input v-model.trim="form.postal_code" outlined label="PSČ" />
            <CountrySelect
              v-model="form.state"
              label="Země sídla"
              hint="U dodavatele výchozí země původu zboží"
              :rules="[rules.notEmpty]"
            />
          </div>

          <!-- Contact Information -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.email" outlined label="Email" type="email" />
            <q-input v-model.trim="form.phone" outlined label="Telefon" />
          </div>

          <!-- Business Settings -->
          <div class="grid grid-cols-2 gap-2">
            <q-input
              v-model.number="form.invoice_due_days"
              outlined
              label="Splatnost (dny)"
              type="number"
            />
            <q-input
              v-model.number="form.block_after_due_days"
              outlined
              label="Blokovat po dnech"
              type="number"
            />
            <InvoicePaymentMethodSelect
              v-model="form.default_payment_method_name"
              label="Výchozí platební metoda"
              hint="Použije se jako předvyplněná metoda při tvorbě faktury."
            />
            <q-select
              v-model="form.customer_group_code"
              :options="customerGroups"
              option-label="name"
              option-value="code"
              emit-value
              map-options
              outlined
              label="Skupina"
              :rules="[rules.notEmpty]"
            />
          </div>

          <!-- Minimum item value -->
          <CustomerMinimumValueFields
            v-model:minimum-item-value="form.minimum_item_value"
            :disable="!form.minimum_item_value_enabled"
          />

          <!-- Invoicing currency -->
          <CustomerCurrencySelect v-model="form.currency" />

          <!-- Note -->
          <q-input v-model.trim="form.note" outlined type="textarea" rows="3" label="Poznámka" />

          <!-- Switches -->
          <div class="flex flex-col gap-4">
            <ToggleRow
              v-model="form.is_self"
              label="Naše firma"
              description="Zákazník představuje naši vlastní firmu. Použije se jako dodavatel na vystavených fakturách. Může existovat pouze jedna."
            />
            <ToggleRow
              v-model="form.is_supplier"
              label="Dodavatel"
              description="Hlavní role zákazníka je dodavatel (vydané objednávky). Pokud je vypnuto, jde o odběratele s přijatými objednávkami. Určuje pouze, co se zobrazuje v detailu zákazníka."
            />
            <ToggleRow
              v-model="form.requires_origin_country"
              data-test="requires-origin-country"
              label="Vyžaduje zemi původu zboží"
              description="Každá položka objednávky tohoto zákazníka musí mít požadovanou zemi původu, jinak nelze objednávku předat do skladu. Země se pak uvádí na faktuře."
            />
            <ToggleRow
              v-model="form.requires_own_codes"
              data-test="requires-own-codes"
              label="Objednává podle vlastních kódů"
              description="Každá položka objednávky tohoto zákazníka musí mít jeho vlastní kód produktu, jinak nelze objednávku potvrdit. Na dokladech se pak uvádí pouze tyto kódy."
            />
            <ToggleRow
              v-model="form.minimum_item_value_enabled"
              label="Zaokrouhlovat na minimální hodnotu položky"
              description="Položky s nižší celkovou cenou se zaokrouhlí nahoru na minimální hodnotu (vlastní, nebo globální). Po vypnutí se minimum pro tohoto zákazníka vůbec neuplatní."
            />
            <ToggleRow
              v-model="form.data_collection_agreement"
              label="GDPR - souhlas se sběrem dat"
              description="Zákazník udělil souhlas se shromažďováním a zpracováním svých osobních údajů."
            />
            <ToggleRow
              v-model="form.marketing_data_use_agreement"
              label="Marketing - souhlas s použitím dat"
              description="Zákazník souhlasí s použitím svých údajů pro marketingové účely a nabídky."
            />
            <ToggleRow
              v-model="form.is_valid"
              label="Platný"
              description="Zákazník je aktivní a lze jej vybírat v nových objednávkách. Vypněte u zákazníků, se kterými již nespolupracujeme."
            />
            <ToggleRow
              v-model="form.is_deleted"
              label="Smazaný"
              description="Zákazník je označen jako smazaný a skrytý ze seznamů. Historie objednávek a faktur zůstává zachována."
            />
          </div>

          <div class="mt-2 flex justify-end">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              :loading="loading"
              :label="submitLabel"
              class="h-[3rem] min-w-[10rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { CustomerCreateOrUpdateSchema, CustomerGroupSchema } from '@/client'
import CustomerCurrencySelect from './CustomerCurrencySelect.vue'
import CustomerMinimumValueFields from '@/components/customer/CustomerMinimumValueFields.vue'
import ToggleRow from '@/components/customer/ToggleRow.vue'
import CountrySelect from '@/components/selects/CountrySelect.vue'
import InvoicePaymentMethodSelect from '@/components/selects/InvoicePaymentMethodSelect.vue'
import { rules } from '@/utils/rules'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<CustomerCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
    customerGroups?: CustomerGroupSchema[]
  }>(),
  {
    title: 'Zákazník',
    submitLabel: 'uložit',
    loading: false,
    customerGroups: () => [],
  },
)

const customerTypeOptions = [
  { label: 'Firma', value: 'FIRMA' },
  { label: 'Osoba', value: 'OSOBA' },
]

const priceTypeOptions = [{ label: 'Firmy', value: 'FIRMY' }]

const emit = defineEmits<{
  (e: 'submit', body: CustomerCreateOrUpdateSchema): void
}>()

const onSubmit = () => {
  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
