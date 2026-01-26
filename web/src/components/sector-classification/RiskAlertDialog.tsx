'use client'

import { AlertTriangle } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { RiskAlertDialogProps } from './RiskAlertDialog.types'

export function RiskAlertDialog({
  open,
  onOpenChange,
  onConfirm,
}: RiskAlertDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <AlertDialogTitle>重要提示</AlertDialogTitle>
          </div>
          <AlertDialogDescription asChild>
            <div className="space-y-3 py-4">
              <p className="text-sm">
                本功能提供的板块分类数据仅供参考，不构成任何投资建议。
              </p>
              <p className="text-sm">
                股票市场有风险，投资需谨慎。
              </p>
              <p className="text-sm">
                过往表现不代表未来收益。
              </p>
              <p className="text-sm">
                请根据自己的风险承受能力和投资目标做出独立决策。
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction onClick={onConfirm}>
            我已知晓并理解
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
