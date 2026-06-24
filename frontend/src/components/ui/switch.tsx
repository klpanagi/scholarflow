import * as React from "react"
import { cn } from "@/lib/utils"

export interface SwitchProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  /** Optional label for accessibility */
  label?: string
}

/**
 * Switch — A toggle switch component styled as a slider.
 * Uses a hidden checkbox input for accessibility.
 */
const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, id, label, checked, onChange, disabled, ...props }, ref) => {
    const switchId = id || `switch-${Math.random().toString(36).slice(2, 9)}`

    return (
      <label
        htmlFor={switchId}
        className={cn(
          "relative inline-flex h-5 w-9 cursor-pointer items-center rounded-full transition-colors duration-200",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-500 focus-visible:ring-offset-2",
          checked
            ? "bg-gold-500"
            : "bg-input",
          disabled && "cursor-not-allowed opacity-50",
          className,
        )}
        aria-label={label}
      >
        <input
          ref={ref}
          id={switchId}
          type="checkbox"
          role="switch"
          aria-checked={checked}
          checked={checked}
          onChange={onChange}
          disabled={disabled}
          className="peer sr-only"
          {...props}
        />
        <span
          className={cn(
            "pointer-events-none block h-4 w-4 rounded-full bg-white shadow-sm ring-0 transition-transform duration-200",
            checked ? "translate-x-[18px]" : "translate-x-[2px]",
          )}
        />
      </label>
    )
  },
)
Switch.displayName = "Switch"

export { Switch }
