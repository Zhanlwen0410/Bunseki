/** API / analysis shapes (subset; backend may return more fields). */

export type ApiError = {
  code: string
  message: string
  hint?: string
}

export type AnalyzeResponse =
  | { ok: true; result: AnalysisResult; profile: ProfileRow[] }
  | { ok: false; error: ApiError }

export type AnalysisResult = {
  source_text: string
  tokens: TokenRow[]
  lemma_frequency: Record<string, number>
  domain_frequency: Record<string, number>
  summary: {
    token_count: number
    unique_lemma_count: number
    [k: string]: unknown
  }
  [k: string]: unknown
}

export type TokenRow = {
  surface?: string
  lemma?: string
  domain_code?: string
  domain_codes?: string[]
  domain_labels?: string[]
  domain_label?: string
  pos?: string
  offset?: number
  [k: string]: unknown
}

export type ProfileRow = {
  domain_code: string
  count: number
  label?: string
  unique_lemma_count?: number
  [k: string]: unknown
}

export type KwicRow = {
  line?: number
  left?: string
  key?: string
  right?: string
  domain_code?: string
  source_offset?: number
  sentence_index?: number
  previous?: string
  current?: string
  next?: string
  confidence?: number
  [k: string]: unknown
}

export type LexiconDomainRow = {
  domain_code: string
  domain_label: string
  count: number
  words: string[]
}

export type ComparisonPayload = {
  lemma_comparison: { key: string; left_count: number; right_count: number; delta: number }[]
  domain_comparison: { key: string; left_count: number; right_count: number; delta: number }[]
  summary: Record<string, number>
}
