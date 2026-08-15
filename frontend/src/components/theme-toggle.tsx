"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="w-9 h-9 rounded-xl bg-zinc-800/40 border border-zinc-700/50" />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="relative p-2 rounded-xl bg-zinc-800/60 dark:bg-zinc-800/60 hover:bg-zinc-700/80 border border-zinc-700/60 text-zinc-300 dark:text-zinc-200 transition-all shadow-md flex items-center justify-center cursor-pointer"
      title={isDark ? "Açık Temaya Geç" : "Koyu Temaya Geç"}
      aria-label="Toggle Theme"
    >
      {isDark ? (
        <Sun className="w-4 h-4 text-amber-400 transition-transform rotate-0 hover:rotate-45" />
      ) : (
        <Moon className="w-4 h-4 text-sky-400 transition-transform -rotate-12 hover:rotate-0" />
      )}
    </button>
  );
}
