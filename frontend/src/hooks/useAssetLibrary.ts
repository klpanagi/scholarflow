import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AssetSummary, AssetListResponse } from '../types/chat'

/**
 * Fetch the current user's asset (paper) library.
 *
 * Supports paginated listing via `GET /assets/` and optional free-text search
 * via `GET /assets/search`. When a `query` is provided the search endpoint is
 * used; otherwise the standard paginated list is returned.
 *
 * Results are normalised to `{ items: AssetSummary[], total, page, size }`.
 */
export function useAssetLibrary(query = '', page = 1, size = 50) {
  return useQuery({
    queryKey: ['assetLibrary', query, page, size],
    queryFn: async () => {
      if (query.trim()) {
        // Search endpoint — returns an array (not paginated)
        const { data } = await api.get<AssetSummary[]>(
          `/assets/search?q=${encodeURIComponent(query)}&limit=${size}`,
        )
        return {
          items: data as AssetSummary[],
          total: data.length,
          page,
          size,
        }
      }

      // Standard paginated list
      const { data } = await api.get<AssetListResponse>(
        `/assets/?page=${page}&size=${size}`,
      )
      return data
    },
    staleTime: 30_000,
  })
}
