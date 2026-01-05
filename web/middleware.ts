import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Next.js 中间件 - 路由保护
 *
 * 功能：
 * 1. 检查用户是否已登录（通过认证令牌）
 * 2. 未登录用户访问受保护路由时重定向到登录页
 * 3. 登录后自动跳转回原始请求页面
 */

// 受保护的路由列表
const protectedRoutes = ['/dashboard']

// 公开路由（不需要认证）
const publicRoutes = ['/login', '/register', '/verify-email', '/forgot-password']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // 检查是否是受保护的路由
  const isProtectedRoute = protectedRoutes.some(route =>
    pathname.startsWith(route)
  )

  // 检查是否是公开路由
  const isPublicRoute = publicRoutes.some(route =>
    pathname.startsWith(route)
  )

  // 如果不是受保护路由，直接放行
  if (!isProtectedRoute) {
    return NextResponse.next()
  }

  // 获取认证令牌
  const token = request.cookies.get('access_token')?.value ||
               request.cookies.get('refresh_token')?.value

  // 如果已访问受保护路由但没有令牌，重定向到登录页
  if (isProtectedRoute && !token) {
    // 保存原始路径，登录后可以跳转回来
    const redirectUrl = encodeURIComponent(pathname + request.nextUrl.search)
    const loginUrl = `/login?redirect=${redirectUrl}`

    return NextResponse.redirect(new URL(loginUrl, request.url))
  }

  // 如果已登录用户访问登录页，重定向到 dashboard
  if (isPublicRoute && token) {
    const redirectParam = request.nextUrl.searchParams.get('redirect')
    return NextResponse.redirect(new URL(redirectParam || '/dashboard', request.url))
  }

  return NextResponse.next()
}

/**
 * 匹配路径配置
 *
 * Matcher 是一个数组，包含要匹配的路径模式：
 * - `/dashboard/:path*` 匹配所有 /dashboard 开头的路由
 * - `/login` 匹配登录页
 * - `/register` 匹配注册页
 *
 * 排除路径：
 * - 排除静态文件（_next/static, _next/image, favicon.ico 等）
 */
export const config = {
  matcher: [
    /*
     * 匹配所有路径，除了：
     * - _next/static (静态文件)
     * - _next/image (图片优化文件)
     * - favicon.ico (网站图标)
     * - public 文件夹中的文件
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
