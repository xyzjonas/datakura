import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import UsersTable from '@/components/settings/users/UsersTable.vue'

const mocks = vi.hoisted(() => ({
  getUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  whoami: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesUsersGetUsers: mocks.getUsers,
  warehouseApiRoutesUsersCreateUser: mocks.createUser,
  warehouseApiRoutesUsersUpdateUser: mocks.updateUser,
  warehouseApiRoutesUsersDeleteUser: mocks.deleteUser,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown }) => response.data,
  }),
}))

vi.mock('@/composables/use-auth', async () => {
  const { ref } = await import('vue')
  const user = ref({ user_id: 1 })
  return { useAuth: () => ({ user, whoami: mocks.whoami }) }
})

const mountTable = () =>
  mount(UsersTable, {
    global: {
      stubs: {
        QTable: {
          props: ['rows'],
          template: `
            <div>
              <div v-for="row in rows" :key="row.id" :data-row="row.username">
                <slot name="body-cell-username" :row="row" />
                <slot name="body-cell-actions" :row="row" />
              </div>
            </div>
          `,
        },
        QTd: { template: '<div><slot /></div>' },
        QBtn: {
          props: ['icon', 'disable'],
          emits: ['click'],
          template:
            '<button :data-icon="icon" :disabled="disable" @click="$emit(\'click\')"><slot /></button>',
        },
        QTooltip: true,
        SearchInput: true,
        UserUpsertDialog: true,
        ConfirmDialog: {
          props: ['show'],
          emits: ['confirm'],
          template:
            '<div v-if="show"><button data-test="confirm" @click="$emit(\'confirm\')" /></div>',
        },
      },
    },
  })

describe('UsersTable', () => {
  beforeEach(() => {
    Object.values(mocks).forEach((m) => typeof m === 'function' && m.mockReset())
    mocks.getUsers.mockResolvedValue({
      data: {
        data: [
          { id: 1, username: 'admin', is_superuser: true, is_active: true },
          { id: 2, username: 'bob', is_superuser: false, is_active: true },
        ],
      },
    })
  })

  it('lists users and disables deleting own account', async () => {
    const wrapper = mountTable()
    await flushPromises()

    const own = wrapper.get('[data-row="admin"] [data-icon="delete"]')
    const other = wrapper.get('[data-row="bob"] [data-icon="delete"]')
    expect(own.attributes('disabled')).toBeDefined()
    expect(other.attributes('disabled')).toBeUndefined()
  })

  it('deletes another user after confirmation', async () => {
    mocks.deleteUser.mockResolvedValue({ data: { data: { id: 2 } } })
    const wrapper = mountTable()
    await flushPromises()

    await wrapper.get('[data-row="bob"] [data-icon="delete"]').trigger('click')
    await wrapper.get('[data-test="confirm"]').trigger('click')
    await flushPromises()

    expect(mocks.deleteUser).toHaveBeenCalledWith({ path: { user_id: 2 } })
    expect(mocks.getUsers).toHaveBeenCalledTimes(2)
  })
})
