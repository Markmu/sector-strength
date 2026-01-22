/**
 * 板块分类排序工具函数
 */

import type { SectorClassification } from '@/types/sector-classification'
import type { SortColumn, SortOrder } from '@/stores/useSectorClassificationSort'

/**
 * 对板块分类数据进行排序
 *
 * @param data - 分类数据列表
 * @param sortBy - 排序列
 * @param sortOrder - 排序方向
 * @returns 排序后的数据
 *
 * @description
 * - classification_level: 按数值排序（1-9）
 * - sector_name: 按中文字母顺序排序
 * - change_percent: 按数值排序（支持正负零）
 */
export function sortClassifications(
  data: SectorClassification[],
  sortBy: SortColumn,
  sortOrder: SortOrder
): SectorClassification[] {
  const sorted = [...data].sort((a, b) => {
    let comparison = 0

    switch (sortBy) {
      case 'classification_level':
        // 数值排序：分类级别
        comparison = a.classification_level - b.classification_level
        break

      case 'sector_name':
        // 中文排序：使用 localeCompare 支持中文字符
        comparison = a.sector_name.localeCompare(b.sector_name, 'zh-CN')
        break

      case 'change_percent':
        // 数值排序：涨跌幅（正负零）
        comparison = a.change_percent - b.change_percent
        break
    }

    // 根据排序方向返回结果
    return sortOrder === 'asc' ? comparison : -comparison
  })

  return sorted
}
