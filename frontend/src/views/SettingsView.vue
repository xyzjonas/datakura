<template>
  <div class="flex flex-1 gap-5">
    <div class="flex flex-col h-full min-w-xs">
      <q-scroll-area class="flex-1 p-2">
        <h1 class="mb-5 text-lg">NASTAVENÍ</h1>
        <q-list class="flex flex-col gap-1" separator>
          <q-item
            v-for="item in items"
            :key="item.key"
            clickable
            v-ripple
            :active="item.key === selectedTab"
            active-class="bg-primary text-light"
            :class="{ 'rounded-md': true, uppercase: true }"
            dense
            @click="selectedTab = item.key"
          >
            <q-item-section avatar>
              <q-icon :name="item.icon" />
            </q-item-section>
            <q-item-section> {{ item.label }} </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </div>
    <q-separator vertical />
    <div class="flex-1">
      <Suspense>
        <component :is="selectedTabComponent" />
        <template #fallback>
          <div>...loading inner</div>
        </template>
      </Suspense>
    </div>
  </div>
</template>

<script setup lang="ts">
import MissingSettingsTab from '@/components/settings/MissingSettingsTab.vue'
import PackagingSettingsTab from '@/components/settings/PackagingSettingsTab.vue'
import { useLocalStorage } from '@vueuse/core'
import { ref, watch, type Component } from 'vue'

const selectedTab = useLocalStorage('settings-selected-tab', 'packaging')
const selectedTabComponent = ref<Component>()

watch(
  selectedTab,
  (value: string) => {
    if (value === 'packaging') {
      selectedTabComponent.value = PackagingSettingsTab
    } else {
      selectedTabComponent.value = MissingSettingsTab
    }
  },
  { immediate: true },
)

const items = [
  {
    key: 'packaging',
    label: 'balení',
    icon: 'sym_o_package_2',
  },
  {
    key: 'users',
    label: 'uživatelé',
    icon: 'sym_o_group',
  },
]
</script>

<style lang="scss" scoped></style>
