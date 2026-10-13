<template>
  <div class="flex items-center gap-5">
    <UserAvatar :username="user.username" :url="user.avatar_url" :size="96" />
    <div class="flex flex-col gap-2 items-start">
      <q-btn outline color="primary" icon="sym_o_upload" label="nahrát obrázek" @click="pickFile" />
      <q-btn
        v-if="user.avatar_url"
        flat
        color="negative"
        icon="delete"
        label="odebrat"
        :loading="saving"
        @click="removeAvatar"
      />
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="hidden"
        data-test="avatar-file-input"
        @change="onFileSelected"
      />
    </div>
  </div>

  <AvatarCropDialog v-model:show="showCrop" :src="cropSrc" :loading="saving" @crop="uploadAvatar" />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesAuthDeleteAvatar,
  warehouseApiRoutesAuthUploadAvatar,
  type WhoamiResponse,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useAuth } from '@/composables/use-auth'
import { onBeforeUnmount, ref } from 'vue'
import AvatarCropDialog from './AvatarCropDialog.vue'
import UserAvatar from './UserAvatar.vue'

const { onResponse } = useApi()
const { user } = useAuth()

const fileInput = ref<HTMLInputElement>()
const showCrop = ref(false)
const cropSrc = ref('')
const saving = ref(false)

const revokeSrc = () => {
  if (cropSrc.value) {
    URL.revokeObjectURL(cropSrc.value)
    cropSrc.value = ''
  }
}

onBeforeUnmount(revokeSrc)

const pickFile = () => fileInput.value?.click()

const onFileSelected = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // allow selecting the same file again
  if (!file) {
    return
  }
  revokeSrc()
  cropSrc.value = URL.createObjectURL(file)
  showCrop.value = true
}

const applyUser = (response?: WhoamiResponse) => {
  if (response?.data) {
    user.value = response.data
    return true
  }
  return false
}

const uploadAvatar = async (avatar: File) => {
  saving.value = true
  try {
    if (applyUser(onResponse(await warehouseApiRoutesAuthUploadAvatar({ body: { avatar } })))) {
      showCrop.value = false
    }
  } finally {
    saving.value = false
  }
}

const removeAvatar = async () => {
  saving.value = true
  try {
    applyUser(onResponse(await warehouseApiRoutesAuthDeleteAvatar()))
  } finally {
    saving.value = false
  }
}
</script>
