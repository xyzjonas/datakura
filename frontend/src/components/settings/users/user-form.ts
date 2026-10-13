export type UserFormData = {
  username: string
  password: string
  email: string
  first_name: string
  last_name: string
  is_active: boolean
  is_superuser: boolean
}

export const createDefaultUserForm = (): UserFormData => ({
  username: '',
  password: '',
  email: '',
  first_name: '',
  last_name: '',
  is_active: true,
  is_superuser: false,
})
