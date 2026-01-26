'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Checkbox } from '@/components/ui/Checkbox'
import { AlertCircle } from 'lucide-react'
import type { DataFixDialogProps, SectorOption } from './DataFixDialog.types.ts'

const TIME_RANGE_OPTIONS = [
  { label: '最近 7 天', value: 7 },
  { label: '最近 30 天', value: 30 },
  { label: '最近 90 天', value: 90 },
  { label: '最近 180 天', value: 180 },
]

/**
 * 数据修复弹窗组件
 *
 * @description
 * Story 4.5: Task 1
 * 提供数据修复的表单界面
 *
 * @param open - 是否打开弹窗
 * @param onClose - 关闭弹窗回调
 * @param onComplete - 修复完成回调
 * @param sectors - 可用的板块列表
 */
export function DataFixDialog({
  open,
  onClose,
  onComplete,
  sectors,
}: DataFixDialogProps) {
  const [sectorId, setSectorId] = useState('')
  const [sectorName, setSectorName] = useState('')
  const [days, setDays] = useState(30)
  const [overwrite, setOverwrite] = useState(false)
  const [useIdInput, setUseIdInput] = useState(true)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // 重置表单
  useEffect(() => {
    if (open) {
      setSectorId('')
      setSectorName('')
      setDays(30)
      setOverwrite(false)
      setUseIdInput(true)
      setErrors({})
    }
  }, [open])

  /**
   * 验证表单
   */
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (useIdInput && !sectorId.trim()) {
      newErrors.sectorId = '请输入板块 ID'
    }

    if (!useIdInput && !sectorName.trim()) {
      newErrors.sectorName = '请选择板块'
    }

    if (days <= 0) {
      newErrors.days = '时间范围必须大于 0'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  /**
   * 提交表单
   */
  const handleSubmit = () => {
    if (!validateForm()) {
      return
    }

    const request = {
      sector_id: useIdInput ? sectorId : undefined,
      sector_name: !useIdInput ? sectorName : undefined,
      days,
      overwrite,
    }

    // 调用父组件传递的修复逻辑
    // 父组件会通过 useDataFix hook 完成 API 调用
    if (onComplete) {
      onComplete(request as any)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold text-[#1a1a2e]">
            数据修复
          </DialogTitle>
          <DialogDescription className="text-sm text-[#6c757d]">
            修复异常的分类数据
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 板块选择方式 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              板块选择方式
            </label>
            <div className="flex gap-4">
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="inputMethod"
                  checked={useIdInput}
                  onChange={() => setUseIdInput(true)}
                  className="form-radio h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300"
                />
                <span className="ml-2 text-sm text-gray-700">按 ID</span>
              </label>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="radio"
                  name="inputMethod"
                  checked={!useIdInput}
                  onChange={() => setUseIdInput(false)}
                  className="form-radio h-4 w-4 text-cyan-600 focus:ring-cyan-500 border-gray-300"
                />
                <span className="ml-2 text-sm text-gray-700">按名称</span>
              </label>
            </div>
          </div>

          {/* 板块 ID 输入 */}
          {useIdInput ? (
            <div>
              <Input
                label="板块 ID"
                value={sectorId}
                onChange={(e) => setSectorId(e.target.value)}
                placeholder="输入板块 ID"
                error={errors.sectorId}
              />
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                板块名称
              </label>
              <select
                value={sectorName}
                onChange={(e) => setSectorName(e.target.value)}
                className="w-full px-4 py-2.5 text-sm border border-[#dee2e6] rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-100 focus:border-cyan-400 bg-white"
              >
                <option value="">选择板块</option>
                {sectors.map((sector) => (
                  <option key={sector.id} value={sector.name}>
                    {sector.name}
                  </option>
                ))}
              </select>
              {errors.sectorName && (
                <p className="mt-1.5 text-sm text-red-600">{errors.sectorName}</p>
              )}
            </div>
          )}

          {/* 时间范围 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              时间范围
            </label>
            <div className="grid grid-cols-2 gap-2">
              {TIME_RANGE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setDays(option.value)}
                  className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                    days === option.value
                      ? 'bg-cyan-500 text-white border-cyan-500'
                      : 'bg-white text-gray-700 border-[#dee2e6] hover:bg-gray-50'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            {errors.days && (
              <p className="mt-1.5 text-sm text-red-600">{errors.days}</p>
            )}
          </div>

          {/* 覆盖选项 */}
          <div className="flex items-center">
            <Checkbox
              id="overwrite"
              checked={overwrite}
              onCheckedChange={setOverwrite}
            />
            <label
              htmlFor="overwrite"
              className="ml-2 text-sm text-gray-700 cursor-pointer"
            >
              覆盖已有数据
            </label>
          </div>

          {/* 警告提示 */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-900">
                <p className="font-semibold mb-1">注意</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>修复操作会重新计算分类数据</li>
                  <li>如果未勾选"覆盖已有数据"，只会修复缺失的板块</li>
                  <li>此操作会记录到审计日志</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* 按钮 */}
        <div className="flex justify-end gap-3">
          <Button
            onClick={onClose}
            variant="outline"
            type="button"
          >
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            variant="primary"
            type="button"
          >
            开始修复
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
