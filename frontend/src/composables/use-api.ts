import type { BaseResponse } from '@/client'
import { useQuasar } from 'quasar'

// interface ResponseStub<D extends BaseResponse | undefined> {
//   data: D
//   error: unknown
//   request: Request
//   response: Response
// }

type ResponseStub<D> = (
  | {
      data: undefined
      error: unknown
    }
  | {
      data: D
      error: undefined
    }
) & {
  request: Request
  response: Response
}

export function isBaseResponse(obj: unknown | undefined): obj is BaseResponse {
  return typeof obj === 'object' && !!obj && 'success' in obj && 'message' in obj
}

export const useApi = () => {
  const $q = useQuasar()

  const onResponse = <D>(response: ResponseStub<D>): D | undefined => {
    if (response.error) {
      $q.notify({
        message: 'Generická chyba',
        type: 'negative',
      })
      return undefined
    }
    if (response.data !== undefined && isBaseResponse(response.data) && !response.data.success) {
      $q.notify({
        message: response.data.message ?? 'Operace selhala',
        type: 'negative',
      })
      return undefined
    }

    return response.data
  }

  return {
    onResponse,
  }
}
