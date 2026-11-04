import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SnapshotSchedulesTable from '@/components/settings/snapshot-schedules/SnapshotSchedulesTable.vue'

const mocks = vi.hoisted(() => ({
  getSchedules: vi.fn(),
  createSchedule: vi.fn(),
  updateSchedule: vi.fn(),
  deleteSchedule: vi.fn(),
}))

vi.mock('@/client', () => ({
  warehouseApiRoutesSnapshotSchedulesGetSnapshotSchedules: mocks.getSchedules,
  warehouseApiRoutesSnapshotSchedulesCreateSnapshotSchedule: mocks.createSchedule,
  warehouseApiRoutesSnapshotSchedulesUpdateSnapshotSchedule: mocks.updateSchedule,
  warehouseApiRoutesSnapshotSchedulesDeleteSnapshotSchedule: mocks.deleteSchedule,
}))

vi.mock('@/composables/use-api', () => ({
  useApi: () => ({
    onResponse: (response: { data?: unknown }) => response.data,
  }),
}))

const schedule = {
  id: 7,
  name: 'Měsíční',
  enabled: true,
  mode: 'day_of_month',
  day_of_month: 15,
  hour: 2,
  minute: 0,
  last_run_at: null,
  total_run_count: 0,
}

const mountTable = () =>
  mount(SnapshotSchedulesTable, {
    global: {
      stubs: {
        QTable: {
          props: ['rows'],
          template: `
            <div>
              <slot name="top-right" />
              <div v-for="row in rows" :key="row.id">
                <slot name="body-cell-schedule" :row="row" />
                <slot name="body-cell-enabled" :row="row" />
                <slot name="body-cell-actions" :row="row" />
              </div>
            </div>
          `,
        },
        QTd: { template: '<div><slot /></div>' },
        QBtn: {
          props: ['label', 'icon'],
          emits: ['click'],
          template: '<button :data-icon="icon" @click="$emit(\'click\')">{{ label }}</button>',
        },
        QToggle: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template:
            '<button data-test="toggle" @click="$emit(\'update:modelValue\', !modelValue)" />',
        },
        QTooltip: { template: '<div><slot /></div>' },
        SnapshotScheduleUpsertDialog: { props: ['show', 'modelValue'], template: '<div />' },
        ConfirmDialog: {
          props: ['show', 'title'],
          emits: ['confirm', 'update:show'],
          template:
            '<div v-if="show"><slot /><button data-test="confirm-delete" @click="$emit(\'confirm\')">ok</button></div>',
        },
      },
    },
  })

describe('SnapshotSchedulesTable', () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset())
    mocks.getSchedules.mockResolvedValue({ data: { data: [schedule] } })
  })

  it('loads and describes schedules', async () => {
    const wrapper = mountTable()
    await flushPromises()

    expect(wrapper.text()).toContain('Každého 15. v měsíci v 02:00')
  })

  it('toggles enabled flag keeping the rest of the schedule', async () => {
    mocks.updateSchedule.mockResolvedValue({ data: { data: schedule } })
    const wrapper = mountTable()
    await flushPromises()

    await wrapper.get('[data-test="toggle"]').trigger('click')
    await flushPromises()

    expect(mocks.updateSchedule).toHaveBeenCalledWith({
      path: { schedule_id: 7 },
      body: {
        name: 'Měsíční',
        enabled: false,
        mode: 'day_of_month',
        day_of_month: 15,
        hour: 2,
        minute: 0,
      },
    })
    expect(mocks.getSchedules).toHaveBeenCalledTimes(2)
  })

  it('deletes a schedule after confirmation and reloads', async () => {
    mocks.deleteSchedule.mockResolvedValue({ data: { data: schedule } })
    const wrapper = mountTable()
    await flushPromises()

    await wrapper.get('[data-icon="delete"]').trigger('click')
    await wrapper.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()

    expect(mocks.deleteSchedule).toHaveBeenCalledWith({ path: { schedule_id: 7 } })
    expect(mocks.getSchedules).toHaveBeenCalledTimes(2)
  })

  it('does not reload when the delete fails', async () => {
    mocks.deleteSchedule.mockResolvedValue({ data: undefined })
    const wrapper = mountTable()
    await flushPromises()

    await wrapper.get('[data-icon="delete"]').trigger('click')
    await wrapper.get('[data-test="confirm-delete"]').trigger('click')
    await flushPromises()

    expect(mocks.getSchedules).toHaveBeenCalledTimes(1)
  })
})
