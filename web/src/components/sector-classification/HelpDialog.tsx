'use client'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { HelpDialogProps } from './HelpDialog.types'

export function HelpDialog({ open, onOpenChange }: HelpDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>板块强弱分类说明</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* 分类级别说明 */}
          <section>
            <h3 className="text-lg font-semibold mb-3">分类级别说明</h3>
            <p className="text-sm text-gray-600 mb-4">
              根据板块当前价格相对于不同均线的位置，将板块分为9类：
            </p>
            <ul className="space-y-2">
              <li className="flex items-start">
                <span className="font-semibold text-green-600 mr-2 min-w-[60px]">第 9 类</span>
                <span className="text-sm">最强，价格在所有均线上方</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-green-500 mr-2 min-w-[60px]">第 8 类</span>
                <span className="text-sm">攻克 240 日线</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-green-400 mr-2 min-w-[60px]">第 7 类</span>
                <span className="text-sm">攻克 120 日线</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-lime-500 mr-2 min-w-[60px]">第 6 类</span>
                <span className="text-sm">攻克 90 日线</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-yellow-500 mr-2 min-w-[60px]">第 5 类</span>
                <span className="text-sm">攻克 60 日线</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-orange-400 mr-2 min-w-[60px]">第 4 类</span>
                <span className="text-sm">攻克 30 日线</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-orange-500 mr-2 min-w-[60px]">第 3 类</span>
                <span className="text-sm">攻克 20 日线</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-red-400 mr-2 min-w-[60px]">第 2 类</span>
                <span className="text-sm">攻克 10 日线</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-red-600 mr-2 min-w-[60px]">第 1 类</span>
                <span className="text-sm">最弱，价格在所有均线下方</span>
              </li>
            </ul>
          </section>

          {/* 反弹/调整状态说明 */}
          <section>
            <h3 className="text-lg font-semibold mb-3">反弹/调整状态</h3>
            <ul className="space-y-2">
              <li className="flex items-start">
                <span className="font-semibold text-green-600 mr-2 min-w-[60px]">反弹</span>
                <span className="text-sm">当前价格高于 5 天前价格</span>
              </li>
              <li className="flex items-start">
                <span className="font-semibold text-red-600 mr-2 min-w-[60px]">调整</span>
                <span className="text-sm">当前价格低于 5 天前价格</span>
              </li>
            </ul>
          </section>

          {/* 缠论理论说明（可选） */}
          <section className="pt-4 border-t">
            <p className="text-xs text-gray-500 leading-relaxed">
              <strong>理论依据：</strong>板块强弱分类基于缠中说禅理论，通过分析价格与均线的位置关系来判断板块强弱。
              均线周期包括 5、10、20、30、60、90、120、240 天。
            </p>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  )
}
