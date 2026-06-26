import { useState } from "react";
import { Link } from "react-router-dom";
import { LogOut, Settings } from "lucide-react";
import { useAuthStore } from "@/stores/auth";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface UserMenuProps {
  align?: "start" | "end" | "center";
  side?: "top" | "bottom" | "left" | "right";
  className?: string;
}

export function UserMenu({ align = "end", side = "top", className }: UserMenuProps) {
  const { user, logout } = useAuthStore();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  const initials = user.name
    .split(" ")
    .map((n) => n.charAt(0))
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            "flex items-center gap-2.5 rounded-lg p-1.5 outline-none",
            "transition-colors duration-200",
            "hover:bg-gold-500/10 data-[state=open]:bg-gold-500/10",
            "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            className,
          )}
          aria-label={`User menu for ${user.name}`}
        >
          <div
            className={cn(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
              "bg-gradient-to-br from-gold-400 to-gold-600",
              "text-xs font-bold tracking-wide text-white",
              "shadow-sm shadow-gold-500/20",
            )}
          >
            {initials}
          </div>
          <span
            className={cn(
              "text-sm font-medium truncate max-w-[9rem]",
              "text-slate-800 dark:text-navy-100",
            )}
          >
            {user.name}
          </span>
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align={align}
        side={side}
        sideOffset={6}
        className={cn(
          "w-56 z-50 backdrop-blur-xl",
          "bg-white/95 border-slate-200 text-slate-800",
          "dark:bg-navy-800/95 dark:border-navy-700/50 dark:text-navy-100",
        )}
      >
        <DropdownMenuLabel
          className={cn(
            "flex flex-col gap-0.5 px-3 py-2",
            "text-slate-500 dark:text-navy-200",
          )}
        >
          <span className="font-semibold text-sm text-slate-900 dark:text-navy-50">
            {user.name}
          </span>
          <span className="text-xs truncate">{user.email}</span>
        </DropdownMenuLabel>

        <DropdownMenuSeparator className="bg-slate-200 dark:bg-navy-700/50" />

        <DropdownMenuItem asChild>
          <Link
            to="/settings"
            className={cn(
              "flex items-center gap-2.5 px-3 py-2 text-sm rounded-md cursor-pointer outline-none",
              "transition-colors duration-150",
              "text-slate-600 dark:text-navy-200",
              "focus:bg-gold-500/10 focus:text-gold-700 dark:focus:text-gold-300",
            )}
          >
            <Settings aria-hidden="true" className="h-4 w-4 shrink-0" />
            Settings
          </Link>
        </DropdownMenuItem>

        <DropdownMenuSeparator className="bg-slate-200 dark:bg-navy-700/50" />

        <DropdownMenuItem asChild>
          <button
            onClick={() => logout()}
            className={cn(
              "flex items-center gap-2.5 w-full px-3 py-2 text-sm rounded-md cursor-pointer outline-none",
              "transition-colors duration-150",
              "text-red-500 hover:bg-red-500/10 focus:bg-red-500/10",
            )}
          >
            <LogOut aria-hidden="true" className="h-4 w-4 shrink-0" />
            Log out
          </button>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
