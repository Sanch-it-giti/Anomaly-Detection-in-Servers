import raw from './generated/evidence.json'
export type Row = Record<string, string | number | boolean | null>
export type Artifact = { id: string; path: string; scope: string; status: 'available' | 'unavailable'; reason?: string; sha256?: string; url?: string; rows?: Row[]; data?: unknown }
export const snapshot = raw as unknown as { signature: string; artifacts: Artifact[]; readOnly: boolean }
export const artifact = (id: string) => snapshot.artifacts.find(a => a.id === id)
export const rows = (id: string): Row[] => artifact(id)?.status === 'available' ? artifact(id)?.rows ?? [] : []
export const object = (data: unknown): Record<string, unknown> => typeof data === 'object' && data !== null && !Array.isArray(data) ? data as Record<string, unknown> : {}
export const json = (id: string) => artifact(id)?.status === 'available' ? object(artifact(id)?.data) : {}
export const number = (row: Row | undefined, key: string): number | null => typeof row?.[key] === 'number' ? row[key] as number : null
export const format = (n: number | null | undefined, digits = 3) => n == null ? 'Unavailable' : n.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits })
export const percent = (n: number | null) => n == null ? 'Unavailable' : `${(n * 100).toFixed(2)}%`
export const policies = ['persistence', 'arima', 'xgboost', 'adaptive']
export const names: Record<string, string> = { persistence: 'Persistence', arima: 'ARIMA', xgboost: 'XGBoost', adaptive: 'Frozen adaptive', shadow_arima: 'Fixed ARIMA shadow', shadow_xgboost: 'Fixed XGBoost shadow' }
export const colors: Record<string, string> = { persistence: '#a9afa1', arima: '#2c3325', xgboost: '#ed672c', adaptive: '#877b65' }
