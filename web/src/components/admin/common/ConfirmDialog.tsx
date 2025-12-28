"use client";

import React, { useEffect, useRef } from 'react';
import { X, AlertTriangle, Info, CheckCircle, AlertCircle } from 'lucide-react';

/**
 * 对话框类型
 */
type DialogType = 'default' | 'info' | 'success' | 'warning' | 'danger';

/**
 * ConfirmDialog 组件
 *
 * 确认对话框组件
 *
 * @example
 * ```tsx
 * <ConfirmDialog
 *   open={isOpen}
 *   title="确认删除"
 *   message="确定要删除这条记录吗？此操作不可撤销。"
 *   type="danger"
 *   onConfirm={() => handleDelete()}
 *   onCancel={() => setIsOpen(false)}
 * />
 * ```
 */

interface ConfirmDialogProps {
  /** 是否打开对话框 */
  open: boolean;
  /** 对话框标题 */
  title: string;
  /** 对话框内容 */
  message: string;
  /** 对话框类型 */
  type?: DialogType;
  /** 确认按钮文本 */
  confirmText?: string;
  /** 取消按钮文本 */
  cancelText?: string;
  /** 确认按钮类型 */
  confirmVariant?: 'primary' | 'danger';
  /** 确认回调 */
  onConfirm: () => void | Promise<void>;
  /** 取消回调 */
  onCancel: () => void;
  /** 是否加载中 */
  loading?: boolean;
}

const typeConfig = {
  default: { icon: null, bgColor: 'bg-gray-50', iconColor: 'text-gray-600' },
  info: { icon: Info, bgColor: 'bg-blue-50', iconColor: 'text-blue-600' },
  success: { icon: CheckCircle, bgColor: 'bg-green-50', iconColor: 'text-green-600' },
  warning: { icon: AlertTriangle, bgColor: 'bg-yellow-50', iconColor: 'text-yellow-600' },
  danger: { icon: AlertCircle, bgColor: 'bg-red-50', iconColor: 'text-red-600' },
};

export default function ConfirmDialog({
  open,
  title,
  message,
  type = 'default',
  confirmText = '确认',
  cancelText = '取消',
  confirmVariant = 'primary',
  onConfirm,
  onCancel,
  loading = false,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // 处理 ESC 键关闭
  useEffect(() => {
    if (!open) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading) {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onCancel, loading]);

  // 点击背景关闭
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !loading) {
      onCancel();
    }
  };

  if (!open) return null;

  const config = typeConfig[type];
  const Icon = config.icon;

  const confirmButtonClass =
    confirmVariant === 'danger'
      ? 'bg-red-600 hover:bg-red-700 text-white border-red-600'
      : 'bg-blue-600 hover:bg-blue-700 text-white border-blue-600';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        className="w-full max-w-md rounded-lg bg-white shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        aria-describedby="dialog-message"
      >
        {/* 内容 */}
        <div className="p-6">
          {/* 图标和标题 */}
          <div className="flex items-start gap-4">
            {Icon && (
              <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full ${config.bgColor}`}>
                <Icon className={`h-5 w-5 ${config.iconColor}`} />
              </div>
            )}
            <div className="flex-1">
              <h3
                id="dialog-title"
                className="text-lg font-semibold text-gray-900"
              >
                {title}
              </h3>
              <p
                id="dialog-message"
                className="mt-2 text-sm text-gray-600"
              >
                {message}
              </p>
            </div>
            {/* 关闭按钮 */}
            <button
              onClick={onCancel}
              disabled={loading}
              className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* 底部按钮 */}
        <div className="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2 text-sm font-medium border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 ${confirmButtonClass}`}
          >
            {loading && (
              <svg
                className="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            )}
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
