export { default as Button } from './Button'
export type { ButtonProps } from './Button'

export { default as Input } from './Input'
export type { InputProps } from './Input'

export { Card, CardHeader, CardBody, CardFooter } from './Card'
export type { CardProps, CardHeaderProps, CardBodyProps, CardFooterProps } from './Card'

export { default as Table } from './Table'
export type { TableColumn, TableProps } from './Table'

// 小写别名以支持 @/components/ui/table 导入方式
export { default as table } from './Table'
export type { TableColumn as tableColumn, TableProps as tableProps } from './Table'

export { default as Loading } from './Loading'
export type { LoadingProps } from './Loading'

export { default as Modal } from './Modal'
export type { ModalProps } from './Modal'