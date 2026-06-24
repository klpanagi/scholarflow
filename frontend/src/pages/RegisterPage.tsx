import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useAuthStore } from "@/stores/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"
import { Loader2, Eye, EyeOff, User, Mail, Lock, Github } from "lucide-react"
import { cn } from "@/lib/utils"

const registerSchema = z
  .object({
    fullName: z.string().min(2, "Name must be at least 2 characters"),
    email: z.string().email("Please enter a valid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
      .regex(/[a-z]/, "Password must contain at least one lowercase letter")
      .regex(/[0-9]/, "Password must contain at least one number"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  })

type RegisterForm = z.infer<typeof registerSchema>

function getPasswordStrength(password: string): {
  score: number
  label: string
  barClass: string
  textClass: string
} {
  let score = 0
  if (password.length >= 8) score++
  if (/[0-9]/.test(password)) score++
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++
  if (/[A-Z]/.test(password)) score++

  if (score === 0) return { score: 0, label: "", barClass: "", textClass: "" }
  if (score <= 1) return { score, label: "Weak", barClass: "bg-red-500", textClass: "text-red-500" }
  if (score === 2) return { score, label: "Medium", barClass: "bg-amber-500", textClass: "text-amber-500" }
  if (score === 3) return { score, label: "Strong", barClass: "bg-gold-500", textClass: "text-gold-500" }
  return { score: 4, label: "Excellent", barClass: "bg-emerald-500", textClass: "text-emerald-500" }
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const { register: registerUser } = useAuthStore()
  const { toast } = useToast()
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  })

  const passwordValue = watch("password") || ""
  const strength = getPasswordStrength(passwordValue)

  const onSubmit = async (data: RegisterForm) => {
    setAuthError(null)
    try {
      await registerUser(data.email, data.password, data.fullName)
      navigate("/dashboard")
    } catch (error: any) {
      const msg = error.response?.data?.detail || "Could not create account"
      setAuthError(msg)
      toast({
        title: "Registration failed",
        description: msg,
        variant: "destructive",
      })
    }
  }

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="text-center">
        <h1 className="text-3xl tracking-tight text-foreground">
          Create your account
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Start your academic journey with ScholarFlow
        </p>
      </div>

      {/* ── OAuth Buttons (visual only) ── */}
      <div className="grid grid-cols-2 gap-3">
        <Button
          variant="outline"
          className="gap-2 bg-background/40 hover:bg-background/60 border-border/40"
          type="button"
          onClick={() => {}}
          aria-label="Continue with Google"
        >
          <svg aria-hidden="true" className="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          <span className="text-xs sm:text-sm">Google</span>
        </Button>
        <Button
          variant="outline"
          className="gap-2 bg-background/40 hover:bg-background/60 border-border/40"
          type="button"
          onClick={() => {}}
          aria-label="Continue with GitHub"
        >
          <Github aria-hidden="true" className="h-4 w-4 shrink-0" />
          <span className="text-xs sm:text-sm">GitHub</span>
        </Button>
      </div>

      {/* ── Divider ── */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-border/40" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-card px-3 text-muted-foreground/60">or</span>
        </div>
      </div>

      {/* ── Auth Error ── */}
      {authError && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive animate-in">
          {authError}
        </div>
      )}

      {/* ── Form ── */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {/* Full Name */}
        <div className="space-y-1.5">
          <label htmlFor="fullName" className="sr-only">
            Full name
          </label>
          <div className="relative">
            <User aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <Input
              id="fullName"
              placeholder="Full name"
              autoComplete="name"
              aria-invalid={!!errors.fullName}
              aria-describedby={errors.fullName ? "fullName-error" : undefined}
              className={cn(
                "h-11 pl-10 bg-background/50 border-border/40",
                "focus-visible:ring-gold-500/40 focus-visible:border-gold-500/50",
                errors.fullName &&
                  "border-destructive/50 focus-visible:ring-destructive/40 focus-visible:border-destructive/50"
              )}
              {...register("fullName")}
            />
          </div>
          {errors.fullName && (
            <p id="fullName-error" className="text-xs text-destructive flex items-center gap-1">
              <span aria-hidden="true" className="inline-block w-1 h-1 rounded-full bg-destructive shrink-0" />
              {errors.fullName.message}
            </p>
          )}
        </div>

        {/* Email */}
        <div className="space-y-1.5">
          <label htmlFor="email" className="sr-only">
            Email address
          </label>
          <div className="relative">
            <Mail aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <Input
              id="email"
              type="email"
              placeholder="Email address"
              autoComplete="email"
              aria-invalid={!!errors.email}
              aria-describedby={errors.email ? "email-error" : undefined}
              className={cn(
                "h-11 pl-10 bg-background/50 border-border/40",
                "focus-visible:ring-gold-500/40 focus-visible:border-gold-500/50",
                errors.email &&
                  "border-destructive/50 focus-visible:ring-destructive/40 focus-visible:border-destructive/50"
              )}
              {...register("email")}
            />
          </div>
          {errors.email && (
            <p id="email-error" className="text-xs text-destructive flex items-center gap-1">
              <span aria-hidden="true" className="inline-block w-1 h-1 rounded-full bg-destructive shrink-0" />
              {errors.email.message}
            </p>
          )}
        </div>

        {/* Password */}
        <div className="space-y-1.5">
          <label htmlFor="password" className="sr-only">
            Password
          </label>
          <div className="relative">
            <Lock aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              autoComplete="new-password"
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? "password-error" : "password-strength"}
              className={cn(
                "h-11 pl-10 pr-10 bg-background/50 border-border/40",
                "focus-visible:ring-gold-500/40 focus-visible:border-gold-500/50",
                errors.password &&
                  "border-destructive/50 focus-visible:ring-destructive/40 focus-visible:border-destructive/50"
              )}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded transition-colors"
              tabIndex={-1}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && (
            <p id="password-error" className="text-xs text-destructive flex items-center gap-1">
              <span aria-hidden="true" className="inline-block w-1 h-1 rounded-full bg-destructive shrink-0" />
              {errors.password.message}
            </p>
          )}
        </div>

        {/* ── Password Strength Indicator ── */}
        {passwordValue.length > 0 && (
          <div id="password-strength" aria-live="polite" className="space-y-1.5 -mt-1">
            <div
              role="meter"
              aria-label="Password strength"
              aria-valuemin={0}
              aria-valuemax={4}
              aria-valuenow={strength.score}
              aria-valuetext={strength.label || "Not evaluated"}
              className="flex gap-1"
            >
              {[1, 2, 3, 4].map((segment) => (
                <div
                  key={segment}
                  aria-hidden="true"
                  className={cn(
                    "h-1 flex-1 rounded-full transition-all duration-300",
                    segment <= strength.score ? strength.barClass : "bg-border/20"
                  )}
                />
              ))}
            </div>
            {strength.label && (
              <p className={cn("text-xs font-medium", strength.textClass)}>
                {strength.label}
              </p>
            )}
          </div>
        )}

        {/* Confirm Password */}
        <div className="space-y-1.5">
          <label htmlFor="confirmPassword" className="sr-only">
            Confirm password
          </label>
          <div className="relative">
            <Lock aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <Input
              id="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Confirm password"
              autoComplete="new-password"
              aria-invalid={!!errors.confirmPassword}
              aria-describedby={errors.confirmPassword ? "confirmPassword-error" : undefined}
              className={cn(
                "h-11 pl-10 pr-10 bg-background/50 border-border/40",
                "focus-visible:ring-gold-500/40 focus-visible:border-gold-500/50",
                errors.confirmPassword &&
                  "border-destructive/50 focus-visible:ring-destructive/40 focus-visible:border-destructive/50"
              )}
              {...register("confirmPassword")}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded transition-colors"
              tabIndex={-1}
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
            >
              {showConfirmPassword ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
            </button>
          </div>
          {errors.confirmPassword && (
            <p id="confirmPassword-error" className="text-xs text-destructive flex items-center gap-1">
              <span aria-hidden="true" className="inline-block w-1 h-1 rounded-full bg-destructive shrink-0" />
              {errors.confirmPassword.message}
            </p>
          )}
        </div>

        {/* ── Submit ── */}
        <Button
          type="submit"
          disabled={isSubmitting}
          className={cn(
            "relative h-11 w-full overflow-hidden font-medium text-white",
            "bg-gradient-to-r from-gold-500 to-amber-500",
            "hover:from-gold-600 hover:to-amber-600",
            "shadow-lg shadow-gold-500/15 hover:shadow-gold-500/25",
            "transition-all duration-300",
            "disabled:from-gold-500/50 disabled:to-amber-500/50 disabled:shadow-none"
          )}
        >
          {isSubmitting ? (
            <>
              <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" />
              Creating account...
            </>
          ) : (
            "Create account"
          )}
        </Button>
      </form>

      {/* ── Footer ── */}
      <p className="text-center text-sm text-muted-foreground/80">
        Already have an account?{" "}
        <Link
          to="/login"
          className="font-medium text-gold-500 hover:text-gold-400 transition-colors"
        >
          Sign in
        </Link>
      </p>
    </div>
  )
}
