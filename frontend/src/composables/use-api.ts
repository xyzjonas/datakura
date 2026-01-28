import type { BaseResponse } from '@/client'
import { containsCustomError, isCustomError } from '@/components/type-guards/api-error-response'
import { useQuasar } from 'quasar'

// interface ResponseStub<D extends BaseResponse | undefined> {
//   data: D
//   error: unknown
//   request: Request
//   response: Response
// }

const ERROR_CODES: { [key: string]: { title: string; caption: string } } = {
  PACKAGING_0001: {
    title: 'Chybné balení',
    caption: 'Položka nelze rozdělit do požadovaného balení beze zbytku!',
  },
}

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
    if (response.response.ok) {
      return response.data
    }
    console.info(response)
    const statusCode = response.response.status
    let message = 'Neočekávaná chyba, kontaktujte administrátora'
    let caption = response.response.statusText

    // custom app error codes (handled exceptions)
    console.info(response.error)
    if (containsCustomError(response.error) && isCustomError(response.error.error)) {
      const localeVersion = ERROR_CODES[response.error.error.error_code]
      message = localeVersion?.title ?? response.error.error.error_code // todo: locale translate BE codes
      caption = localeVersion?.caption ?? `${response.error.error.exception}`
    }

    $q.notify({
      message: message,
      caption: `${statusCode}: ${caption}`,
      type: 'negative',
    })
    return undefined
  }

  return {
    onResponse,
  }
}
