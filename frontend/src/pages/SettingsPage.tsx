import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { useToast } from '../hooks/use-toast'

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

const PROVIDER_DISPLAY: Record<string, { name: string; color: string }> = {
  'opencode': { name: 'OpenCode Go', color: 'bg-blue-500' },
  'opencode-zen': { name: 'OpenCode Zen', color: 'bg-purple-500' },
  'openrouter': { name: 'OpenRouter', color: 'bg-orange-500' },
  'openai': { name: 'OpenAI', color: 'bg-green-500' },
}

export function SettingsPage() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [testResults, setTestResults] = useState<Record<string, { status: string; message?: string }>>({})
  const [embProvider, setEmbProvider] = useState('')
  const [embModel, setEmbModel] = useState('')

  const { data: settings, isLoading } = useQuery<SettingsData>({
    queryKey: ['settings'],
    queryFn: async () => {
      const { data } = await api.get('/settings/providers')
      return data
    },
  })

  useEffect(() => {
    if (settings) {
      setEmbProvider(settings.embedding_provider)
      setEmbModel(settings.embedding_model)
    }
  }, [settings])

  const embeddingModels = settings?.embedding_models || {}
  const allEmbeddingModels = Object.values(embeddingModels).flat()
  const currentEmbModels = embProvider && embeddingModels[embProvider] ? embeddingModels[embProvider] : allEmbeddingModels

  const saveEmbeddingMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/settings/embedding', { provider: embProvider, model: embModel })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      toast({ title: 'Saved', description: 'Embedding configuration updated.' })
    },
    onError: () => {
      toast({ title: 'Error', description: 'Failed to save embedding config', variant: 'destructive' })
    },
  })

  const testMutation = useMutation({
    mutationFn: async (provider: string) => {
      const { data } = await api.post(`/settings/providers/test?provider=${provider}`)
      return data
    },
    onSuccess: (data, provider) => {
      setTestResults(prev => ({
        ...prev,
        [provider]: { status: data.status, message: data.message || data.response }
      }))
      toast({
        title: data.status === 'connected' ? 'Connected' : 'Failed',
        description: data.message || data.response || `Status: ${data.status}`,
        variant: data.status === 'connected' ? 'default' : 'destructive',
      })
    },
    onError: (_err, provider) => {
      setTestResults(prev => ({
        ...prev,
        [provider]: { status: 'error', message: 'Request failed' }
      }))
      toast({ title: 'Error', description: 'Failed to test provider', variant: 'destructive' })
    },
  })

  if (isLoading) return <div className="p-8">Loading settings...</div>

  const providers = settings?.providers || {}

  return (
    <div className="container mx-auto p-6 max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      
      <div className="space-y-6">

        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Embedding Configuration</CardTitle>
            <CardDescription>
              Provider and model used for paper indexing and semantic search.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <label className="text-xs font-medium mb-1 block text-muted-foreground">Provider</label>
                <select
                  value={embProvider}
                  onChange={(e) => { setEmbProvider(e.target.value); setEmbModel('') }}
                  className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                >
                  <option value="">Select provider</option>
                  {Object.keys(embeddingModels).length > 0
                    ? Object.keys(embeddingModels).map((p) => (
                        <option key={p} value={p}>{PROVIDER_DISPLAY[p]?.name || p}</option>
                      ))
                    : Object.keys(providers).filter(p => providers[p]?.configured).map((p) => (
                        <option key={p} value={p}>{PROVIDER_DISPLAY[p]?.name || p}</option>
                      ))
                  }
                </select>
              </div>
              <div className="flex-1">
                <label className="text-xs font-medium mb-1 block text-muted-foreground">Model</label>
                <select
                  value={embModel}
                  onChange={(e) => setEmbModel(e.target.value)}
                  className="w-full border rounded-md px-3 py-2 text-sm bg-background"
                  disabled={!embProvider}
                >
                  <option value="">Select model</option>
                  {currentEmbModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <Button
                size="sm"
                onClick={() => saveEmbeddingMutation.mutate()}
                disabled={!embProvider || !embModel || saveEmbeddingMutation.isPending}
              >
                {saveEmbeddingMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </div>
            {settings?.embedding_provider && (
              <p className="text-xs text-muted-foreground mt-2">
                Active: {PROVIDER_DISPLAY[settings.embedding_provider]?.name || settings.embedding_provider} → {settings.embedding_model}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">LLM Providers</CardTitle>
            <CardDescription>
              API keys are configured via environment variables. Test connectivity below.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(providers).map(([provider, status]) => {
                const display = PROVIDER_DISPLAY[provider] || { name: provider, color: 'bg-gray-500' }
                const testResult = testResults[provider]
                const isTesting = testMutation.isPending && testMutation.variables === provider

                return (
                  <div key={provider} className="flex items-center justify-between py-3 px-4 rounded-lg border">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${status.configured ? 'bg-green-500' : 'bg-zinc-400'}`} />
                      <div>
                        <span className="text-sm font-medium">{display.name}</span>
                        <span className="text-xs text-muted-foreground ml-2">
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
                          setTestResults(prev => { const next = { ...prev }; delete next[provider]; return next })
                          testMutation.mutate(provider)
                        }}
                        disabled={!status.configured || isTesting}
                        className="h-7 text-xs"
                      >
                        {isTesting ? (
                          <span className="flex items-center gap-1">
                            <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            Testing
                          </span>
                        ) : 'Test'}
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-2">Add API keys to your <code className="bg-muted px-1 rounded">.env</code> file:</p>
            <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
{`OPENCODE_GO_API_KEY=...
OPENCODE_GO_API_BASE=https://opencode.ai/zen/go/v1
OPENCODE_ZEN_API_KEY=...
OPENCODE_ZEN_API_BASE=https://opencode.ai/zen/v1
OPENROUTER_API_KEY=...
OPENAI_API_KEY=...`}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
