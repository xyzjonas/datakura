export function getCsrfFromCookie(name?: string) {
  const cookieName = name ?? 'csrftoken'
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, cookieName.length + 1) === cookieName + '=') {
        cookieValue = decodeURIComponent(cookie.substring(cookieName.length + 1))
        break
      }
    }
  }
  return cookieValue
}

function getFromMeta() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
}

export const getCsrfToken = () => getFromMeta()
