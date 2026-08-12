import { Activity, BarChart3, Radar, TrendingUp } from "lucide-react";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

interface AuthShellProps {
  title: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const signals = [
  { label: "板块强度", icon: BarChart3 },
  { label: "趋势定位", icon: TrendingUp },
  { label: "市场信号", icon: Radar },
];

export function AuthShell({ title, description, children, footer }: AuthShellProps) {
  return (
    <main className="grid min-h-[100dvh] bg-background lg:grid-cols-[minmax(19rem,0.82fr)_minmax(30rem,1.18fr)]">
      <section className="relative hidden overflow-hidden border-r border-border bg-primary-50 p-8 lg:flex lg:flex-col lg:justify-between xl:p-12">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-subtle">
            <Activity className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-base font-semibold tracking-tight text-foreground">板块强度</p>
            <p className="text-xs text-muted-foreground">A 股复盘分析工具</p>
          </div>
        </div>

        <div className="max-w-md">
          <p className="text-3xl font-semibold leading-tight tracking-[-0.035em] text-foreground xl:text-4xl">
            从市场噪音中，找到值得复盘的信号。
          </p>
          <p className="mt-4 max-w-[42ch] text-sm leading-6 text-muted-foreground">
            汇总强度、趋势与资金数据，帮助你更快完成盘后判断。
          </p>
        </div>

        <div className="grid gap-2">
          {signals.map(({ label, icon: Icon }) => (
            <div key={label} className="flex items-center gap-2.5 text-xs font-medium text-muted-foreground">
              <Icon className="h-4 w-4 text-primary" aria-hidden="true" />
              <span>{label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="relative flex min-h-[100dvh] items-center justify-center px-4 py-16 sm:px-6">
        <ThemeToggle compact className="absolute right-4 top-4 sm:right-6 sm:top-6" />
        <div className="w-full max-w-sm">
          <div className="mb-7 lg:hidden">
            <div className="mb-6 flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Activity className="h-4 w-4" aria-hidden="true" />
              </div>
              <span className="text-sm font-semibold tracking-tight text-foreground">板块强度</span>
            </div>
          </div>

          <div className="mb-7">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
          </div>

          {children}

          {footer && <div className="mt-6 border-t border-border pt-5 text-sm text-muted-foreground">{footer}</div>}
        </div>
      </section>
    </main>
  );
}
