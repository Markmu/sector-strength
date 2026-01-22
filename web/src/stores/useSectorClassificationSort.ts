/**
 * 板块分类排序状态管理
 *
 * 使用 Zustand 管理表格排序状态（组件本地状态）
 * 支持按分类级别、板块名称、涨跌幅排序
 */

import { create } from 'zustand'

/**
 * 可排序的列
 */
export type SortColumn = 'classification_level' | 'sector_name' | 'change_percent'

/**
 * 排序方向
 */
export type SortOrder = 'asc' | 'desc'

/**
 * 排序状态接口
 */
export interface SectorClassificationSortState {
  /** 当前排序列 */
  sortBy: SortColumn
  /** 当前排序方向 */
  sortOrder: SortOrder
  /** 切换排序列（点击表头时调用） */
  toggleSortBy: (column: SortColumn) => void
  /** 设置排序列和方向 */
  setSortBy: (column: SortColumn, order: SortOrder) => void
  /** 重置排序状态 */
  reset: () => void
}

/**
 * 默认排序配置
 */
const DEFAULT_SORT: SortColumn = 'classification_level'
const DEFAULT_ORDER: SortOrder = 'desc'

/**
 * 板块分类排序状态 Store
 *
 * @description
 * - 默认按分类级别降序排列（第 9 类在前）
 * - 点击同一列切换排序方向（升序/降序）
 * - 点击不同列切换到该列并设置为降序
 */
export const useSectorClassificationSort = create<SectorClassificationSortState>((set) => ({
  // 初始状态
  sortBy: DEFAULT_SORT,
  sortOrder: DEFAULT_ORDER,

  // 切换排序列（点击表头）
  toggleSortBy: (column) =>
    set((state) => ({
      sortBy: column,
      // 如果点击的是当前排序列，切换排序方向
      // 否则设置为降序（新列默认降序）
      sortOrder: state.sortBy === column && state.sortOrder === 'desc' ? 'asc' : 'desc',
    })),

  // 设置排序列和方向
  setSortBy: (column, order) =>
    set({
      sortBy: column,
      sortOrder: order,
    }),

  // 重置排序状态
  reset: () =>
    set({
      sortBy: DEFAULT_SORT,
      sortOrder: DEFAULT_ORDER,
    }),
}))
