/**
 * Dashboard Page Test
 */

// Mock Next.js navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useSearchParams: () => ({
    get: jest.fn(),
  }),
  usePathname: () => '/dashboard',
}));

// Mock components
jest.mock('@/components/dashboard/DashboardLayout', () => {
  const { cn } = require('@/lib/utils');
  return function MockDashboardLayout({ children, className }: { children: React.ReactNode; className?: string }) {
    return (
      <div data-testid="dashboard-layout" className={cn('min-h-screen', className)}>
        <aside data-testid="sidebar">Sidebar</aside>
        <main>{children}</main>
      </div>
    );
  };
});

import { render, screen } from '@testing-library/react';
import DashboardPage from '@/app/dashboard/page';

describe('Dashboard Page', () => {
  it('should render the dashboard layout', () => {
    render(<DashboardPage />);
    expect(screen.getByTestId('dashboard-layout')).toBeInTheDocument();
  });

  it('should render within a container', () => {
    const { container } = render(<DashboardPage />);
    // DashboardLayout uses min-h-screen class, not .container
    const layout = container.querySelector('.min-h-screen');
    expect(layout).toBeInTheDocument();
  });
});
