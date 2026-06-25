import { useCallback, useEffect, useRef, useState } from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme, THEMES, type Theme } from "./ThemeProvider";

const THEME_LABELS: Record<Theme, string> = {
  "dark-navy": "Dark Navy",
  light: "Light",
  nord: "Nord",
  dracula: "Dracula",
  ocean: "Ocean",
  forest: "Forest",
  sunset: "Sunset",
  rose: "Rose",
};

interface ThemeSwatch {
  bg: string;
  fg: string;
  accent: string;
}

/* Colors extracted from themes.css — background, foreground, and accent HSL values */
const THEME_SWATCHES: Record<Theme, ThemeSwatch> = {
  "dark-navy": { bg: "hsl(224, 71%, 4%)", fg: "hsl(213, 31%, 91%)", accent: "hsl(36, 47%, 64%)" },
  light: { bg: "hsl(210, 40%, 98%)", fg: "hsl(222.2, 84%, 4.9%)", accent: "hsl(217, 91%, 60%)" },
  nord: { bg: "hsl(220, 16%, 14%)", fg: "hsl(219, 28%, 88%)", accent: "hsl(193, 43%, 67%)" },
  dracula: { bg: "hsl(231, 15%, 16%)", fg: "hsl(60, 30%, 96%)", accent: "hsl(331, 100%, 71%)" },
  ocean: { bg: "hsl(200, 50%, 8%)", fg: "hsl(190, 20%, 88%)", accent: "hsl(170, 76%, 53%)" },
  forest: { bg: "hsl(150, 30%, 6%)", fg: "hsl(120, 15%, 85%)", accent: "hsl(142, 71%, 45%)" },
  sunset: { bg: "hsl(220, 15%, 8%)", fg: "hsl(30, 25%, 88%)", accent: "hsl(25, 95%, 53%)" },
  rose: { bg: "hsl(340, 10%, 10%)", fg: "hsl(0, 10%, 90%)", accent: "hsl(347, 90%, 60%)" },
};

export function ThemePicker() {
  const { theme: currentTheme, setTheme } = useTheme();
  const [focusedIndex, setFocusedIndex] = useState(() =>
    Math.max(0, THEMES.indexOf(currentTheme)),
  );
  const containerRef = useRef<HTMLDivElement>(null);

  // Keep focusedIndex in sync when currentTheme changes externally
  useEffect(() => {
    setFocusedIndex((prev) => {
      const idx = THEMES.indexOf(currentTheme);
      return idx >= 0 ? idx : prev;
    });
  }, [currentTheme]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      let newIndex = focusedIndex;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        newIndex = (focusedIndex + 1) % THEMES.length;
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        newIndex = (focusedIndex - 1 + THEMES.length) % THEMES.length;
      } else if (e.key === "Home") {
        e.preventDefault();
        newIndex = 0;
      } else if (e.key === "End") {
        e.preventDefault();
        newIndex = THEMES.length - 1;
      } else {
        return;
      }
      setFocusedIndex(newIndex);
      const el = document.getElementById(`theme-${THEMES[newIndex]}`);
      el?.focus();
    },
    [focusedIndex],
  );

  return (
    <div
      ref={containerRef}
      role="radiogroup"
      aria-label="Theme selection"
      onKeyDown={handleKeyDown}
      className="grid grid-cols-2 gap-3 md:grid-cols-4"
    >
      {THEMES.map((theme, index) => {
        const isSelected = theme === currentTheme;
        const isFocused = index === focusedIndex;
        const swatch = THEME_SWATCHES[theme];

        return (
          <button
            key={theme}
            id={`theme-${theme}`}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={THEME_LABELS[theme]}
            tabIndex={isFocused ? 0 : -1}
            onClick={() => setTheme(theme)}
            className={cn(
              "group relative flex flex-col items-center gap-2.5 rounded-lg border p-4 transition-all duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              isSelected
                ? "border-primary/60 bg-primary/[0.04] ring-2 ring-primary/30"
                : "border-border/40 hover:border-primary/50 hover:bg-accent/30",
            )}
          >
            {/* Selected checkmark */}
            {isSelected && (
              <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm">
                <Check aria-hidden="true" className="h-3 w-3" />
              </span>
            )}

            {/* Color swatches */}
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span
                className="h-5 w-5 rounded-full border border-border/30"
                style={{ backgroundColor: swatch.bg }}
              />
              <span
                className="h-5 w-5 rounded-full border border-border/30"
                style={{ backgroundColor: swatch.fg }}
              />
              <span
                className="h-5 w-5 rounded-full border border-border/30"
                style={{ backgroundColor: swatch.accent }}
              />
            </div>

            {/* Theme name */}
            <span className="text-xs font-medium leading-none text-foreground">
              {THEME_LABELS[theme]}
            </span>
          </button>
        );
      })}
    </div>
  );
}
