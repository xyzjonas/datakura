import { warehouseApiRoutesAuthLoginUser, warehouseApiRoutesAuthWhoami } from '@/client'
import { useLocalStorage } from '@vueuse/core'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from './use-api'

interface User {
  id?: number
  username?: string
}

const loginVerified = ref(false) // check session only on 1st page loag
const user = useLocalStorage<User>('session-user', {})
const accessToken = ref<string>()
const refreshToken = useLocalStorage('refresh-token', '')
const csrfToken = useLocalStorage('csrf-token', '')

export const useAuth = () => {
  const { onResponse } = useApi()

  const reset = () => {
    user.value = undefined
    accessToken.value = undefined
    refreshToken.value = undefined
    loginVerified.value = false
  }

  const signin = async (username: string, password: string): Promise<boolean> => {
    const res = await warehouseApiRoutesAuthLoginUser({
      body: {
        username,
        password,
      },
    })

    reset()

    // 401 means a regular failed login
    if (res.response.status === 401) {
      reset()
      return false
    }

    // SUCCESS
    if (res.data?.data?.username) {
      user.value = res.data.data
      loginVerified.value = true
      return true
    }

    // anything else than 401 is unexpected => show a notification
    onResponse(res)
    return false
  }

  const whoami = async () => {
    const result = await warehouseApiRoutesAuthWhoami()
    const data = onResponse(result)
    if (data) {
      user.value = data.data
      loginVerified.value = true
      return user.value
    }
    reset()
    return undefined
  }

  const router = useRouter()
  const signout = async () => {
    try {
      await fetch('/api/v1/auth/logout', {
        method: 'POST',
        // credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `bearer ${accessToken.value}`,
          'X-CSRFToken': csrfToken.value,
        },
      })

      reset()
    } finally {
      router.push({ name: 'login' })
    }
  }

  return {
    user,
    accessToken,
    loginVerified,
    signin,
    signout,
    whoami,
  }
}
