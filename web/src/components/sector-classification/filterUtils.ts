/**
 * 板块分类过滤工具函数
 */

import type { SectorClassification } from '@/types/sector-classification'

/**
 * 对板块分类数据进行搜索过滤
 *
 * @param data - 分类数据列表
 * @param searchQuery - 搜索关键词
 * @returns 过滤后的数据
 *
 * @description
 * - 空搜索返回所有数据
 * - 不区分大小写
 * - 支持部分匹配（包含关键词即可）
 * - 自动 trim 首尾空格
 * - 支持中文搜索
 * - 处理 undefined/null 边界情况
 */
export function filterClassifications(
  data: SectorClassification[],
  searchQuery: string
): SectorClassification[] {
  // 处理 undefined/null 边界情况
  if (!searchQuery || !searchQuery.trim()) {
    return data
  }

  const query = searchQuery.toLowerCase().trim()

  return data.filter((item) =>
    item.sector_name.toLowerCase().includes(query)
  )
}
