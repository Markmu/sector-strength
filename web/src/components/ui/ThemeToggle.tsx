"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
  compact?: boolean;
  className?: string;
}

function subscribeToTheme(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => observer.disconnect();
}

function getThemeSnapshot() {
  return document.documentElement.classList.contains("dark");
}

export function ThemeToggle({ compact = false, className }: ThemeToggleProps) {
  const isDark = useSyncExternalStore(subscribeToTheme, getThemeSnapshot, () => false);

  const toggleTheme = () => {
    const nextDark = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", nextDark);
    document.documentElement.classList.toggle("light", !nextDark);
    localStorage.setItem("sector-theme", nextDark ? "dark" : "light");
  };

  const label = isDark ? "切换到浅色主题" : "切换到深色主题";
  const Icon = isDark ? Sun : Moon;

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        "inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-border bg-card px-2.5 text-sm font-medium text-muted-foreground",
        "transition-colors duration-200 hover:border-primary/50 hover:bg-secondary hover:text-foreground",
        "active:translate-y-px",
        compact && "w-9 px-0",
        className,
      )}
      aria-label={label}
      title={label}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      {!compact && <span>{isDark ? "浅色" : "深色"}</span>}
    </button>
  );
}
