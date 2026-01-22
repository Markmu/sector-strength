/**
 * 板块分类搜索状态管理
 *
 * 使用 Zustand 管理搜索状态（组件本地状态）
 * 支持按板块名称搜索过滤
 */

import { create } from 'zustand'

/**
 * 搜索状态接口
 */
export interface SectorClassificationSearchState {
  /** 搜索关键词 */
  searchQuery: string
  /** 设置搜索关键词 */
  setSearchQuery: (query: string) => void
  /** 清除搜索 */
  clearSearch: () => void
}

/**
 * 板块分类搜索状态 Store
 *
 * @description
 * - 默认为空字符串（显示所有板块）
 * - 实时搜索（输入时即时更新）
 * - 与排序状态独立，可组合使用
 */
export const useSectorClassificationSearch = create<SectorClassificationSearchState>((set) => ({
  // 初始状态：空搜索
  searchQuery: '',

  // 设置搜索关键词
  setSearchQuery: (query) =>
    set({ searchQuery: query }),

  // 清除搜索
  clearSearch: () =>
    set({ searchQuery: '' }),
}))
