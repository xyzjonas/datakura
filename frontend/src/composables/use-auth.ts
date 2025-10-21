import { useLocalStorage } from '@vueuse/core'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

interface User {
  id?: number
  username?: string
}

const user = useLocalStorage<User>('session-user', {})
const accessToken = ref<string>()
const refreshToken = useLocalStorage('refresh-token', '')
const csrfToken = useLocalStorage('csrf-token', '')

export const useAuth = () => {
  const signin = async (): Promise<void> => {
    // const res = await daysApiRoutesAuthLoginUser({
    //   body: {
    //     username,
    //     password,
    //   },
    // })
    // // const response = await fetch('/api/v1/auth/login', {
    // //   method: 'POST',
    // //   headers: {
    // //     'Content-Type': 'application/json',
    // //   },
    // //   body: JSON.stringify({
    // //     username: username,
    // //     password: password,
    // //   }),
    // // })
    // if ([403, 401].includes(res.response.status)) {
    //   const body = res.data
    //   return {
    //     isSuccess: false,
    //     message: `...failed to login, ${body?.message ?? 'unknown reason'}`,
    //   }
    // }
    // if (!res.response.ok) {
    //   return {
    //     isSuccess: false,
    //     message: `...failed to login (${res.response.status})`,
    //   }
    // }
    // const body = res.data?.data
    // user.value = {
    //   id: body?.user_id,
    //   username: body?.username,
    // }
    // return {
    //   isSuccess: true,
    //   message: 'Sign in successful',
    // }
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

      user.value = undefined
      accessToken.value = undefined
      refreshToken.value = undefined
    } finally {
      router.push({ name: 'home' })
    }
  }

  return {
    user,
    accessToken,
    signin,
    signout,
  }
}
