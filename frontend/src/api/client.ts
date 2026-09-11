// Thin fetch wrapper. Replaced/extended by TanStack Query hooks starting in
// Phase 5 (submitter API) and Phase 6 (moderator API); kept minimal here so
// Phase 0 has one real, working call to prove frontend -> backend connectivity.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/healthz/`)
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }
  return response.json()
}
