"use client";

import React from 'react';

/**
 * 表格列定义
 */
export interface Column<T = any> {
  /** 列标识 */
  key: string;
  /** 列标题 */
  title: string;
  /** 渲染单元格内容 */
  render?: (value: any, record: T, index: number) => React.ReactNode;
  /** 列宽度 */
  width?: string | number;
  /** 对齐方式 */
  align?: 'left' | 'center' | 'right';
  /** 是否固定列 */
  fixed?: 'left' | 'right';
}

/**
 * AdminTable 组件
 *
 * 管理员页面数据表格组件
 *
 * @example
 * ```tsx
 * const columns: Column<User>[] = [
 *   { key: 'name', title: '姓名' },
 *   { key: 'email', title: '邮箱' },
 * ];
 *
 * <AdminTable
 *   columns={columns}
 *   data={users}
 *   loading={isLoading}
 * />
 * ```
 */

interface AdminTableProps<T = any> {
  /** 列定义 */
  columns: Column<T>[];
  /** 数据源 */
  data: T[];
  /** 是否加载中 */
  loading?: boolean;
  /** 是否显示边框 */
  bordered?: boolean;
  /** 表格大小 */
  size?: 'small' | 'middle' | 'large';
  /** 空数据提示 */
  emptyText?: string;
  /** 行 key */
  rowKey?: string | ((record: T) => string);
  /** 自定义类名 */
  className?: string;
  /** 行点击事件 */
  onRowClick?: (record: T, index: number) => void;
}

export default function AdminTable<T extends Record<string, any>>({
  columns,
  data,
  loading = false,
  bordered = true,
  size = 'middle',
  emptyText = '暂无数据',
  rowKey = 'id',
  className = '',
  onRowClick,
}: AdminTableProps<T>) {
  // 获取行 key
  const getRowKey = (record: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record);
    }
    return record[rowKey] || String(index);
  };

  // 获取单元格值
  const getCellValue = (record: T, column: Column<T>, index: number) => {
    if (column.render) {
      return column.render(record[column.key], record, index);
    }
    return record[column.key];
  };

  // 大小对应的 padding
  const sizeClasses = {
    small: 'py-2 px-3',
    middle: 'py-3 px-4',
    large: 'py-4 px-5',
  };

  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className={`min-w-full ${bordered ? 'border border-gray-200' : ''}`}>
        {/* 表头 */}
        <thead className={`bg-gray-50 ${bordered ? 'border-b border-gray-200' : ''}`}>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={`text-xs font-medium uppercase text-gray-500 ${
                  sizeClasses[size]
                } ${
                  column.align === 'center'
                    ? 'text-center'
                    : column.align === 'right'
                    ? 'text-right'
                    : 'text-left'
                }`}
                style={{ width: column.width }}
              >
                {column.title}
              </th>
            ))}
          </tr>
        </thead>

        {/* 表体 */}
        <tbody className={`divide-y ${bordered ? 'divide-gray-200' : 'divide-gray-100'}`}>
          {loading ? (
            <tr>
              <td
                colSpan={columns.length}
                className="py-8 text-center text-sm text-gray-500"
              >
                加载中...
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="py-8 text-center text-sm text-gray-500"
              >
                {emptyText}
              </td>
            </tr>
          ) : (
            data.map((record, rowIndex) => (
              <tr
                key={getRowKey(record, rowIndex)}
                className={`transition-colors hover:bg-gray-50 ${
                  onRowClick ? 'cursor-pointer' : ''
                }`}
                onClick={() => onRowClick?.(record, rowIndex)}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`text-sm text-gray-700 ${sizeClasses[size]} ${
                      column.align === 'center'
                        ? 'text-center'
                        : column.align === 'right'
                        ? 'text-right'
                        : 'text-left'
                    }`}
                  >
                    {getCellValue(record, column, rowIndex)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
