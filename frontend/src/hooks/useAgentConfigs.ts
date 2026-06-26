import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AgentConfig } from '../types/chat'

/**
 * Fetch all agent configs for the current user.
 *
 * Auto-seeds defaults on first call (backend behaviour). Data is cached for
 * 60 s to avoid hammering the endpoint while the user browses the agent picker.
 */
export function useAgentConfigs() {
  return useQuery({
    queryKey: ['agentConfigs'],
    queryFn: async () => {
      const { data } = await api.get<AgentConfig[]>('/agents/configs')
      return data
    },
    staleTime: 60_000,
  })
}
