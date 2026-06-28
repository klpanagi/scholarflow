import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { api, exportSkillsAndAgents, importSkillsAndAgents } from '../lib/api'
import type { ImportPreviewPayload, ImportResultPayload } from '../types/chat'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Switch } from '../components/ui/switch'
import { Select } from '../components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import ImportPreviewModal from '../components/ImportPreviewModal'
import { PageHeader } from '../components/shared/PageHeader'
import { ModalShell } from '../components/shared/ModalShell'
import { ConfirmDialog } from '../components/shared/ConfirmDialog'
import { ThemePicker } from '../components/theme/ThemePicker'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../hooks/use-toast'
import { cn } from '../lib/utils'
import {
  User,
  Key,
  Settings2,
  CreditCard,
  Loader2,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Camera,
  Globe,
  Bell,
  Shield,
  ExternalLink,
  Download,
  Upload,
  FileJson,
} from 'lucide-react'

// ────────────────────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────────────────────

interface ProviderStatus {
  configured: boolean
  api_base: string
  display_name?: string
}

interface SettingsData {
  providers: Record<string, ProviderStatus>
  models: Record<string, string[]>
  embedding_models: Record<string, string[]>
  embedding_provider: string
  embedding_model: string
}

interface ApiKeyEntry {
  service: string
  is_active: boolean
  created_at: string
}

// ────────────────────────────────────────────────────────────────────────────
// Schemas
// ────────────────────────────────────────────────────────────────────────────

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Must contain one uppercase letter')
      .regex(/[a-z]/, 'Must contain one lowercase letter')
      .regex(/[0-9]/, 'Must contain one number'),
    confirmPassword: z.string(),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type PasswordForm = z.infer<typeof passwordSchema>

// ────────────────────────────────────────────────────────────────────────────
// Constants
// ────────────────────────────────────────────────────────────────────────────

type TabId = 'profile' | 'api-keys' | 'preferences' | 'billing' | 'import-export'

interface TabDef {
  id: TabId
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const TABS: TabDef[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'api-keys', label: 'API Keys', icon: Key },
  { id: 'preferences', label: 'Preferences', icon: Settings2 },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'import-export', label: 'Import/Export', icon: Download },
]

const PROVIDER_DISPLAY: Record<string, { name: string; color: string }> = {
  opencode: { name: 'OpenCode Go', color: 'bg-blue-500' },
  'opencode-zen': { name: 'OpenCode Zen', color: 'bg-purple-500' },
  openrouter: { name: 'OpenRouter', color: 'bg-orange-500' },
  openai: { name: 'OpenAI', color: 'bg-green-500' },
}

const ACADEMIC_SERVICES = [
  {
    id: 'semantic_scholar',
    name: 'Semantic Scholar',
    description:
      'Higher rate limits for paper search (free at semanticscholar.org/product/api)',
  },
  {
    id: 'crossref',
    name: 'CrossRef',
    description: 'Faster DOI and citation lookups',
  },
  {
    id: 'openalex',
    name: 'OpenAlex',
    description:
      'Optional API key for polite pool (faster responses). Use your email as the API key.',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    description: 'Access GPT models through OpenAI API',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: 'Multi-model access through OpenRouter API',
  },
]

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'el', label: '\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac' },
  { value: 'fr', label: 'Fran\u00e7ais' },
  { value: 'de', label: 'Deutsch' },
  { value: 'es', label: 'Espa\u00f1ol' },
]

// ────────────────────────────────────────────────────────────────────────────
// Sidebar Nav
// ────────────────────────────────────────────────────────────────────────────

function SidebarNav({
  tabs,
  activeTab,
  onTabChange,
}: {
  tabs: TabDef[]
  activeTab: TabId
  onTabChange: (id: TabId) => void
}) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = tabs.findIndex((t) => t.id === activeTab)
    if (currentIndex === -1) return
    let nextIndex = currentIndex
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault()
      nextIndex = (currentIndex + 1) % tabs.length
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault()
      nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
    } else if (e.key === 'Home') {
      e.preventDefault()
      nextIndex = 0
    } else if (e.key === 'End') {
      e.preventDefault()
      nextIndex = tabs.length - 1
    } else {
      return
    }
    onTabChange(tabs[nextIndex].id)
    const nextId = `settings-tab-${tabs[nextIndex].id}`
    const el = document.getElementById(nextId)
    el?.focus()
  }

  return (
    <div
      role="tablist"
      aria-label="Settings sections"
      aria-orientation="vertical"
      onKeyDown={handleKeyDown}
      className="flex shrink-0 flex-row gap-1 overflow-x-auto lg:w-52 lg:flex-col"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon
        const isActive = tab.id === activeTab
        return (
          <button
            key={tab.id}
            id={`settings-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`settings-panel-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-all duration-200',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
              isActive
                ? 'border border-primary/20 bg-primary/10 text-primary shadow-sm'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            <Icon
              aria-hidden="true"
              className={cn(
                'h-4 w-4 shrink-0 transition-colors',
                isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground',
              )}
            />
            <span>{tab.label}</span>
          </button>
        )
      })}
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Profile Section
// ────────────────────────────────────────────────────────────────────────────

function ProfileSection() {
  const { user } = useAuthStore()
  const { toast } = useToast()

  const [showPassword, setShowPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  })

  const handlePasswordChange = async (_data: PasswordForm) => {
    toast({
      title: 'Coming soon',
      description: 'Password change will be available in a future update.',
    })
  }

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (ev) => {
        setAvatarUrl(ev.target?.result as string)
        toast({ title: 'Avatar updated', description: 'Profile picture changed.' })
      }
      reader.readAsDataURL(file)
    }
  }

  const initials = user?.name
    ? user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : '?'

  return (
    <div className="space-y-8">
      <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User aria-hidden="true" className="h-4 w-4 text-primary" />
            Personal Information
          </CardTitle>
          <CardDescription>Your account details and profile picture</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:gap-8">
            <div className="flex flex-col items-center gap-3">
              <div className="relative">
                <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border-2 border-border/50 bg-muted text-xl font-semibold text-muted-foreground">
                  {avatarUrl ? (
                    <img
                      src={avatarUrl}
                      alt="Avatar"
                      loading="lazy"
                      decoding="async"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <span className="font-display text-2xl text-primary">{initials}</span>
                  )}
                </div>
                <label
                  htmlFor="avatar-upload"
                  className="absolute -bottom-1 -right-1 flex h-7 w-7 cursor-pointer items-center justify-center rounded-full border border-border/50 bg-card shadow-sm transition-colors hover:bg-accent focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background"
                >
                  <Camera aria-hidden="true" className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="sr-only">Upload avatar</span>
                  <input
                    id="avatar-upload"
                    type="file"
                    accept="image/*"
                    className="sr-only"
                    onChange={handleAvatarChange}
                  />
                </label>
              </div>
              <span className="text-xs text-muted-foreground">Click to upload</span>
            </div>

            <div className="flex-1 space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="profile-name">Full Name</Label>
                <Input
                  id="profile-name"
                  value={user?.name || ''}
                  readOnly
                  className="bg-muted/50 text-muted-foreground"
                />
                <p className="text-xs text-muted-foreground">
                  Name is managed via your account registration.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="profile-email">Email</Label>
                <Input
                  id="profile-email"
                  value={user?.email || ''}
                  readOnly
                  className="bg-muted/50 text-muted-foreground"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield aria-hidden="true" className="h-4 w-4 text-primary" />
            Change Password
          </CardTitle>
          <CardDescription>Update your account password</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(handlePasswordChange)} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="current-password">Current Password</Label>
              <div className="relative">
                <Input
                  id="current-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter current password"
                  className={cn(
                    'pr-10',
                    errors.currentPassword &&
                      'border-destructive/50 focus-visible:ring-destructive/40',
                  )}
                  {...register('currentPassword')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
                </button>
              </div>
              {errors.currentPassword && (
                <p className="text-xs text-destructive">{errors.currentPassword.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="new-password">New Password</Label>
              <div className="relative">
                <Input
                  id="new-password"
                  type={showNewPassword ? 'text' : 'password'}
                  placeholder="Enter new password"
                  className={cn(
                    'pr-10',
                    errors.newPassword &&
                      'border-destructive/50 focus-visible:ring-destructive/40',
                  )}
                  {...register('newPassword')}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                  tabIndex={-1}
                  aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                >
                  {showNewPassword ? (
                    <EyeOff aria-hidden="true" className="h-4 w-4" />
                  ) : (
                    <Eye aria-hidden="true" className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.newPassword && (
                <p className="text-xs text-destructive">{errors.newPassword.message}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-1.5">
              <Label htmlFor="confirm-password">Confirm New Password</Label>
              <div className="relative">
                <Input
                  id="confirm-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm new password"
                  className={cn(
                    'pr-10',
                    errors.confirmPassword &&
                      'border-destructive/50 focus-visible:ring-destructive/40',
                  )}
                  {...register('confirmPassword')}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                  tabIndex={-1}
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? (
                    <EyeOff aria-hidden="true" className="h-4 w-4" />
                  ) : (
                    <Eye aria-hidden="true" className="h-4 w-4" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="text-xs text-destructive">{errors.confirmPassword.message}</p>
              )}
            </div>

            {/* Submit */}
            <div className="flex items-center gap-3 pt-2">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-primary text-primary-foreground hover:bg-primary/90 focus-visible:ring-primary"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  'Update Password'
                )}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => reset()}
                disabled={isSubmitting}
              >
                Reset
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// API Keys Section
// ────────────────────────────────────────────────────────────────────────────

function ApiKeysSection() {
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({})
  const [testResults, setTestResults] = useState<
    Record<string, { status: string; message?: string }>
  >({})
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [newKeyService, setNewKeyService] = useState('semantic_scholar')
  const [newKeyValue, setNewKeyValue] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const { data: settings } = useQuery<SettingsData>({
    queryKey: ['settings'],
    queryFn: async () => {
      const { data } = await api.get('/settings/providers')
      return data
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

  const { data: apiKeys = [] } = useQuery<ApiKeyEntry[]>({
    queryKey: ['api-keys'],
    queryFn: async () => {
      const { data } = await api.get('/settings/api-keys')
      return data
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

  const saveApiKeyMutation = useMutation({
    mutationFn: async ({
      service,
      api_key,
    }: {
      service: string
      api_key: string
    }) => {
      const { data } = await api.post('/settings/api-keys', { service, api_key })
      return data
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setKeyInputs((prev) => ({ ...prev, [vars.service]: '' }))
      setAddDialogOpen(false)
      setNewKeyValue('')
      toast({ title: 'Saved', description: `${vars.service} API key saved.` })
    },
    onError: (_err, vars) => {
      toast({
        title: 'Error',
        description: `Failed to save ${vars.service} key`,
        variant: 'destructive',
      })
    },
  })

  const deleteApiKeyMutation = useMutation({
    mutationFn: async (service: string) => {
      const { data } = await api.delete(`/settings/api-keys/${service}`)
      return data
    },
    onSuccess: (_data, service) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setDeleteTarget(null)
      toast({ title: 'Deleted', description: `${service} API key removed.` })
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to delete API key', variant: 'destructive' })
    },
  })

  const testMutation = useMutation({
    mutationFn: async (provider: string) => {
      const { data } = await api.post(`/settings/providers/test?provider=${provider}`)
      return data
    },
    onSuccess: (data, provider) => {
      setTestResults((prev) => ({
        ...prev,
        [provider]: { status: data.status, message: data.message || data.response },
      }))
      toast({
        title: data.status === 'connected' ? 'Connected' : 'Failed',
        description: data.message || data.response || `Status: ${data.status}`,
        variant: data.status === 'connected' ? 'default' : 'destructive',
      })
    },
    onError: (_err, provider) => {
      setTestResults((prev) => ({
        ...prev,
        [provider]: { status: 'error', message: 'Request failed' },
      }))
      toast({ title: 'Error', description: 'Failed to test provider', variant: 'destructive' })
    },
  })

  const providers = settings?.providers || {}

  const handleAddKey = () => {
    if (newKeyValue.trim()) {
      saveApiKeyMutation.mutate({ service: newKeyService, api_key: newKeyValue.trim() })
    }
  }

  return (
    <div className="space-y-8">
      {/* LLM Providers */}
      <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Key aria-hidden="true" className="h-4 w-4 text-primary" />
            LLM Providers
          </CardTitle>
          <CardDescription>
            API keys are configured via environment variables. Test connectivity below.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.keys(providers).length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No LLM providers configured.
              </p>
            ) : (
              Object.entries(providers).map(([provider, status]) => {
                const display = PROVIDER_DISPLAY[provider] || {
                  name: provider,
                  color: 'bg-gray-500',
                }
                const testResult = testResults[provider]
                const isTesting = testMutation.isPending && testMutation.variables === provider

                return (
                  <div
                    key={provider}
                    className="flex items-center justify-between rounded-lg border border-border/30 px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'h-2 w-2 rounded-full',
                          status.configured ? 'bg-emerald-500' : 'bg-zinc-400',
                        )}
                      />
                      <div>
                        <span className="text-sm font-medium">{display.name}</span>
                        <span className="ml-2 text-xs text-muted-foreground">
                          {status.configured ? 'Configured' : 'Not configured'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {testResult && !isTesting && (
                        <Badge
                          variant={testResult.status === 'connected' ? 'default' : 'destructive'}
                          className="text-xs"
                        >
                          {testResult.status === 'connected' ? 'Connected' : 'Failed'}
                        </Badge>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setTestResults((prev) => {
                            const next = { ...prev }
                            delete next[provider]
                            return next
                          })
                          testMutation.mutate(provider)
                        }}
                        disabled={!status.configured || isTesting}
                        className="h-7 text-xs"
                      >
                        {isTesting ? (
                          <span className="flex items-center gap-1">
                            <Loader2 aria-hidden="true" className="h-3 w-3 animate-spin" />
                            Testing
                          </span>
                        ) : (
                          'Test'
                        )}
                      </Button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </CardContent>
      </Card>

      {/* Academic API Keys */}
      <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Globe aria-hidden="true" className="h-4 w-4 text-primary" />
                Academic & External API Keys
              </CardTitle>
              <CardDescription>
                Per-user keys for scholarly search and AI APIs. Stored encrypted. Optional —
                works without them at lower rate limits.
              </CardDescription>
            </div>
            <Button
              size="sm"
              onClick={() => {
                setAddDialogOpen(true)
                setNewKeyService('semantic_scholar')
                setNewKeyValue('')
              }}
              className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Plus aria-hidden="true" className="h-3.5 w-3.5" />
              Add Key
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {apiKeys.length === 0 ? (
            <div className="py-6 text-center">
              <Key aria-hidden="true" className="mx-auto mb-2 h-8 w-8 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">No API keys configured yet.</p>
              <p className="mt-1 text-xs text-muted-foreground/60">
                Add keys to unlock higher rate limits and additional features.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {apiKeys.map((entry) => {
                const svc = ACADEMIC_SERVICES.find((s) => s.id === entry.service)
                const isDeleting =
                  deleteApiKeyMutation.isPending && deleteApiKeyMutation.variables === entry.service

                return (
                  <div
                    key={entry.service}
                    className="flex items-center justify-between rounded-lg border border-border/30 px-4 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'h-2 w-2 rounded-full',
                          entry.is_active ? 'bg-emerald-500' : 'bg-zinc-400',
                        )}
                      />
                      <div>
                        <span className="text-sm font-medium">
                          {svc?.name || entry.service}
                        </span>
                        <span className="ml-2 text-xs text-muted-foreground">
                          {entry.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <p className="text-xs text-muted-foreground/60">
                          Added {new Date(entry.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs text-destructive hover:text-destructive"
                      onClick={() => setDeleteTarget(entry.service)}
                      disabled={isDeleting}
                      aria-label={`Delete API key for ${svc?.name || entry.service}`}
                    >
                      {isDeleting ? (
                        <Loader2 aria-hidden="true" className="h-3 w-3 animate-spin" />
                      ) : (
                        <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                )
              })}
            </div>
          )}

          {/* Unconfigured services: show inline inputs */}
          <div className="mt-4 space-y-2">
            {ACADEMIC_SERVICES.filter((s) => !apiKeys.find((k) => k.service === s.id)).map(
              (svc) => {
                const inputValue = keyInputs[svc.id] || ''
                const isSaving =
                  saveApiKeyMutation.isPending &&
                  saveApiKeyMutation.variables?.service === svc.id

                return (
                  <div
                    key={svc.id}
                    className="rounded-lg border border-border/20 px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full bg-zinc-400" />
                      <span className="text-sm font-medium">{svc.name}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">{svc.description}</p>
                      <div className="mt-2 flex max-w-md items-end gap-2">
                      <Input
                        id={`apikey-input-${svc.id}`}
                        type="password"
                        placeholder={`Enter ${svc.name} API key`}
                        value={inputValue}
                        onChange={(e) =>
                          setKeyInputs((prev) => ({ ...prev, [svc.id]: e.target.value }))
                        }
                        className="h-8 text-xs"
                        aria-label={`${svc.name} API key`}
                      />
                      <Button
                        size="sm"
                        className="h-8 text-xs"
                        onClick={() => {
                          if (inputValue.trim()) {
                            saveApiKeyMutation.mutate({
                              service: svc.id,
                              api_key: inputValue.trim(),
                            })
                          }
                        }}
                        disabled={!inputValue.trim() || isSaving}
                      >
                        {isSaving ? (
                          <Loader2 aria-hidden="true" className="h-3 w-3 animate-spin" />
                        ) : (
                          'Save'
                        )}
                      </Button>
                    </div>
                  </div>
                )
              },
            )}
          </div>
        </CardContent>
      </Card>

      {/* Add Key Modal */}
      <ModalShell
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        title="Add API Key"
        description="Select a service and enter your API key."
        size="md"
        footer={
          <>
            <Button variant="ghost" onClick={() => setAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddKey}
              disabled={!newKeyValue.trim() || saveApiKeyMutation.isPending}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {saveApiKeyMutation.isPending ? (
                <>
                  <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Key'
              )}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="add-key-service">Service</Label>
            <Select
              id="add-key-service"
              value={newKeyService}
              onChange={(e) => setNewKeyService(e.target.value)}
              options={ACADEMIC_SERVICES.map((s) => ({ value: s.id, label: s.name }))}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="add-key-value">API Key</Label>
            <Input
              id="add-key-value"
              type="password"
              placeholder="Paste your API key here"
              value={newKeyValue}
              onChange={(e) => setNewKeyValue(e.target.value)}
            />
          </div>
        </div>
      </ModalShell>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
        title="Delete API Key"
        description={
          deleteTarget
            ? `Are you sure you want to remove the API key for "${deleteTarget}"? This action cannot be undone.`
            : ''
        }
        variant="danger"
        confirmText="Delete"
        onConfirm={() => {
          if (deleteTarget) {
            deleteApiKeyMutation.mutate(deleteTarget)
          }
        }}
        loading={deleteApiKeyMutation.isPending}
      />
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Preferences Section
// ────────────────────────────────────────────────────────────────────────────

function PreferencesSection() {
  const { toast } = useToast()
  const [language, setLanguage] = useState('en')
  const [notifications, setNotifications] = useState({
    email: true,
    push: false,
    digest: true,
  })

  const handleNotificationChange = (
    key: keyof typeof notifications,
    checked: boolean,
  ) => {
    setNotifications((prev) => ({ ...prev, [key]: checked }))
    toast({
      title: 'Preference updated',
      description: `Notifications ${checked ? 'enabled' : 'disabled'}.`,
    })
  }

  return (
    <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Settings2 aria-hidden="true" className="h-4 w-4 text-primary" />
            Application Preferences
          </CardTitle>
        <CardDescription>
          Customize your experience — theme, language, and notifications.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6 divide-y divide-border/30">
          {/* Theme */}
          <div className="pb-6">
            <div className="space-y-0.5 mb-4">
              <Label className="text-sm font-medium">Theme</Label>
              <p className="text-xs text-muted-foreground">
                Choose your preferred color theme
              </p>
            </div>
            <ThemePicker />
          </div>

          {/* Language */}
          <div className="flex items-center justify-between py-6">
            <div className="space-y-0.5">
              <Label htmlFor="settings-language" className="text-sm font-medium">Language</Label>
              <p className="text-xs text-muted-foreground">
                Select your preferred interface language
              </p>
            </div>
            <Select
              id="settings-language"
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value)
                toast({
                  title: 'Language updated',
                  description: `Interface language changed to ${LANGUAGE_OPTIONS.find((o) => o.value === e.target.value)?.label}.`,
                })
              }}
              options={LANGUAGE_OPTIONS}
              className="w-40"
            />
          </div>

          {/* Notifications */}
          <div className="space-y-4 pt-6">
            <div>
              <span className="flex items-center gap-2 text-sm font-medium">
                <Bell aria-hidden="true" className="h-4 w-4 text-primary" />
                Notification Preferences
              </span>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Control which notifications you receive
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="notif-email" className="text-sm">
                    Email Notifications
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Receive updates via email
                  </p>
                </div>
                <Switch
                  id="notif-email"
                  checked={notifications.email}
                  onChange={(e) => handleNotificationChange('email', e.target.checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="notif-push" className="text-sm">
                    Push Notifications
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Receive in-browser notifications
                  </p>
                </div>
                <Switch
                  id="notif-push"
                  checked={notifications.push}
                  onChange={(e) => handleNotificationChange('push', e.target.checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="notif-digest" className="text-sm">
                    Weekly Digest
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Get a weekly summary of activity
                  </p>
                </div>
                <Switch
                  id="notif-digest"
                  checked={notifications.digest}
                  onChange={(e) => handleNotificationChange('digest', e.target.checked)}
                />
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Billing Section
// ────────────────────────────────────────────────────────────────────────────

function BillingSection() {
  return (
    <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard aria-hidden="true" className="h-4 w-4 text-primary" />
            Billing & Subscription
          </CardTitle>
        <CardDescription>Manage your plan and payment methods</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center gap-4 py-8 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <CreditCard aria-hidden="true" className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-medium text-foreground">Free Plan</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              You are currently on the <strong>Free</strong> tier.
            </p>
            <p className="text-xs text-muted-foreground/60">
              Upgrade to unlock higher rate limits, priority support, and more.
            </p>
          </div>
          <Button
            disabled
            variant="outline"
            className="mt-2 gap-2 border-primary/30 text-primary"
          >
            <ExternalLink aria-hidden="true" className="h-4 w-4" />
            Upgrade Plan
            <span className="text-xs text-muted-foreground/60">— Coming Soon</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Import / Export Section
// ────────────────────────────────────────────────────────────────────────────

function ImportExportSection() {
  const { toast } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isExporting, setIsExporting] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [importPreview, setImportPreview] = useState<ImportPreviewPayload | null>(null)

  const handleExport = async () => {
    setIsExporting(true)
    try {
      const bundle = await exportSkillsAndAgents()
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `academic-pal-export-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast({ title: 'Export complete' })
    } catch (error: any) {
      toast({
        title: 'Export failed',
        description: error.response?.data?.detail || error.message || 'Unknown error',
        variant: 'destructive',
      })
    } finally {
      setIsExporting(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsImporting(true)
    try {
      const text = await file.text()
      JSON.parse(text)

      if (fileInputRef.current) fileInputRef.current.value = ''

      const preview = await importSkillsAndAgents(file)
      setImportPreview(preview)
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        toast({
          title: 'Invalid JSON file',
          description: 'The selected file is not valid JSON.',
          variant: 'destructive',
        })
      } else {
        toast({
          title: 'Import failed',
          description: error.response?.data?.detail || error.message || 'Unknown error',
          variant: 'destructive',
        })
      }
    } finally {
      setIsImporting(false)
    }
  }

  return (
    <>
    <Card className="border-border/50 bg-card/60 backdrop-blur-xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <FileJson aria-hidden="true" className="h-4 w-4 text-primary" />
          Import / Export
        </CardTitle>
        <CardDescription>
          Export your skills and agents as a JSON bundle, or import from a previously exported file.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Export */}
        <div>
          <h4 className="mb-2 text-sm font-medium text-foreground">Export All Skills &amp; Agents</h4>
          <p className="mb-3 text-sm text-muted-foreground">
            Download a JSON file containing all your custom skills and agent configurations.
          </p>
          <Button onClick={handleExport} disabled={isExporting} variant="outline" className="gap-2">
            {isExporting ? (
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            ) : (
              <Download aria-hidden="true" className="h-4 w-4" />
            )}
            {isExporting ? 'Exporting...' : 'Export'}
          </Button>
        </div>

        {/* Divider */}
        <div className="border-t border-border/50" />

        {/* Import */}
        <div>
          <h4 className="mb-2 text-sm font-medium text-foreground">Import Skills &amp; Agents</h4>
          <p className="mb-3 text-sm text-muted-foreground">
            Select a previously exported JSON file to import skills and agent configurations.
          </p>
          <div className="flex items-center gap-3">
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={isImporting}
              variant="outline"
              className="gap-2"
            >
              {isImporting ? (
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : (
                <Upload aria-hidden="true" className="h-4 w-4" />
              )}
              {isImporting ? 'Analyzing...' : 'Select File'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        </div>
      </CardContent>
    </Card>

    {importPreview && (
      <ImportPreviewModal
        preview={importPreview}
        onClose={() => setImportPreview(null)}
        onComplete={(result: ImportResultPayload) => {
          setImportPreview(null)
          toast({
            title: 'Import complete',
            description: `${result.skills_created} skills, ${result.agent_configs_created} agents created.`,
          })
        }}
      />
    )}
    </>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Main Settings Page
// ────────────────────────────────────────────────────────────────────────────

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('profile')

  const renderContent = () => {
    switch (activeTab) {
      case 'profile':
        return (
          <div
            key="profile"
            id="settings-panel-profile"
            role="tabpanel"
            aria-labelledby="settings-tab-profile"
            tabIndex={0}
            className="focus:outline-none"
          >
            <ProfileSection />
          </div>
        )
      case 'api-keys':
        return (
          <div
            key="api-keys"
            id="settings-panel-api-keys"
            role="tabpanel"
            aria-labelledby="settings-tab-api-keys"
            tabIndex={0}
            className="focus:outline-none"
          >
            <ApiKeysSection />
          </div>
        )
      case 'preferences':
        return (
          <div
            key="preferences"
            id="settings-panel-preferences"
            role="tabpanel"
            aria-labelledby="settings-tab-preferences"
            tabIndex={0}
            className="focus:outline-none"
          >
            <PreferencesSection />
          </div>
        )
      case 'billing':
        return (
          <div
            key="billing"
            id="settings-panel-billing"
            role="tabpanel"
            aria-labelledby="settings-tab-billing"
            tabIndex={0}
            className="focus:outline-none"
          >
            <BillingSection />
          </div>
        )
      case 'import-export':
        return (
          <div
            key="import-export"
            id="settings-panel-import-export"
            role="tabpanel"
            aria-labelledby="settings-tab-import-export"
            tabIndex={0}
            className="focus:outline-none"
          >
            <ImportExportSection />
          </div>
        )
    }
  }

  return (
    <div className="animate-in fade-in duration-500">
      <PageHeader
        title="Settings"
        description="Manage your account, API keys, and application preferences."
      />

      <div className="flex flex-col gap-8 lg:flex-row">
        {/* Sidebar */}
        <SidebarNav tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />

        {/* Main content */}
        <div className="min-w-0 flex-1">{renderContent()}</div>
      </div>
    </div>
  )
}

export default SettingsPage
