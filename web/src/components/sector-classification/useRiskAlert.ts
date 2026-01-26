'use client'

import { useState, useEffect } from 'react'

const STORAGE_KEY = 'riskAlertAcknowledged'

export interface UseRiskAlertReturn {
  open: boolean
  setOpen: (open: boolean) => void
  handleConfirm: () => void
  hasAcknowledged: boolean
}

export function useRiskAlert(): UseRiskAlertReturn {
  const [open, setOpen] = useState(false)
  const [hasAcknowledged, setHasAcknowledged] = useState(false)

  useEffect(() => {
    // 检查用户是否已确认
    const acknowledged = localStorage.getItem(STORAGE_KEY) === 'true'
    setHasAcknowledged(acknowledged)

    // 如果未确认，显示弹窗
    if (!acknowledged) {
      setOpen(true)
    }
  }, [])

  const handleConfirm = () => {
    // 保存确认状态
    localStorage.setItem(STORAGE_KEY, 'true')
    setHasAcknowledged(true)
    // 关闭弹窗
    setOpen(false)
  }

  return {
    open,
    setOpen,
    handleConfirm,
    hasAcknowledged,
  }
}
