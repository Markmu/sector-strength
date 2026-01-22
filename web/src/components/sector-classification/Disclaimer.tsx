/**
 * 免责声明组件
 *
 * 显示金融投资风险提示和免责声明，符合合规要求
 */

'use client'

/**
 * Disclaimer 组件属性
 */
export interface DisclaimerProps {
  /** 自定义类名（可选） */
  className?: string
  /** 免责声明文本（可选，默认使用标准文本） */
  text?: string
  /** 是否显示分隔线（默认 false） */
  showSeparator?: boolean
}

/**
 * 默认免责声明文本
 */
const DEFAULT_TEXT = '数据仅供参考，不构成投资建议。投资有风险，入市需谨慎。'

/**
 * 免责声明组件
 *
 * @description
 * - 显示金融投资风险提示和免责声明
 * - 使用语义化 HTML (<footer>)
 * - 支持自定义文本和样式
 * - 可选的分隔线
 * - 完整的可访问性支持
 *
 * @example
 * ```tsx
 * <Disclaimer />
 * <Disclaimer showSeparator={true} />
 * <Disclaimer text="自定义免责声明内容" />
 * ```
 */
export function Disclaimer({
  className = '',
  text = DEFAULT_TEXT,
  showSeparator = false
}: DisclaimerProps) {
  return (
    <footer
      className={`w-full ${className}`}
      role="contentinfo"
      aria-label="免责声明"
    >
      {showSeparator && (
        <div
          className="border-t border-gray-200 my-4"
          role="separator"
          aria-orientation="horizontal"
        />
      )}
      <div className="text-center py-4 px-6">
        <p className="text-xs text-gray-500 leading-relaxed">
          <span className="font-medium">免责声明：</span>
          {text}
        </p>
      </div>
    </footer>
  )
}
