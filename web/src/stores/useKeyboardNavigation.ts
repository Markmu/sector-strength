/**
 * 板块分类表格键盘导航状态管理
 *
 * 使用 Zustand 管理键盘导航状态（组件本地状态）
 * 支持使用方向键在表格单元格间导航
 */

import { create } from 'zustand'

/**
 * 焦点单元格位置
 */
export interface FocusedCell {
  /** 行索引（从 0 开始） */
  rowIndex: number
  /** 单元格索引（从 0 开始） */
  cellIndex: number
}

/**
 * 键盘导航状态接口
 */
export interface KeyboardNavigationState {
  /** 当前聚焦的单元格位置（null 表示无焦点） */
  focusedCell: FocusedCell | null
  /** 设置焦点到指定单元格 */
  setFocusedCell: (rowIndex: number, cellIndex: number) => void
  /** 清除焦点 */
  clearFocus: () => void
  /** 向上移动一行 */
  moveUp: () => void
  /** 向下移动一行（需要提供总行数以检测边界） */
  moveDown: (maxRows: number) => void
  /** 向左移动一列（需要提供总列数以检测边界） */
  moveLeft: (maxCells: number) => void
  /** 向右移动一列（需要提供总列数以检测边界） */
  moveRight: (maxCells: number) => void
}

/**
 * 板块分类键盘导航状态 Store
 *
 * @description
 * - 初始状态为 null（无焦点）
 * - 支持四个方向键导航（↑/↓/←/→）
 * - 自动处理边界情况（第一行、最后一行、第一列、最后一列）
 * - 与排序和搜索状态独立，可组合使用
 */
export const useKeyboardNavigation = create<KeyboardNavigationState>((set, get) => ({
  // 初始状态：无焦点
  focusedCell: null,

  // 设置焦点到指定单元格
  setFocusedCell: (rowIndex, cellIndex) =>
    set({ focusedCell: { rowIndex, cellIndex } }),

  // 清除焦点
  clearFocus: () =>
    set({ focusedCell: null }),

  // 向上移动一行
  moveUp: () => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.rowIndex === 0) return
    set({
      focusedCell: {
        ...focusedCell,
        rowIndex: focusedCell.rowIndex - 1,
      },
    })
  },

  // 向下移动一行
  moveDown: (maxRows) => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.rowIndex >= maxRows - 1) return
    set({
      focusedCell: {
        ...focusedCell,
        rowIndex: focusedCell.rowIndex + 1,
      },
    })
  },

  // 向左移动一列
  moveLeft: (maxCells) => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.cellIndex === 0) return
    set({
      focusedCell: {
        ...focusedCell,
        cellIndex: focusedCell.cellIndex - 1,
      },
    })
  },

  // 向右移动一列
  moveRight: (maxCells) => {
    const { focusedCell } = get()
    if (!focusedCell || focusedCell.cellIndex >= maxCells - 1) return
    set({
      focusedCell: {
        ...focusedCell,
        cellIndex: focusedCell.cellIndex + 1,
      },
    })
  },
}))
