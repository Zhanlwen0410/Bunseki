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
  layers?: {
    layer1_dictionary_hits?: number
    layer1_dictionary_misses?: number
    layer1_wordnet_backfill_hits?: number
    layer2_vector_hits?: number
    layer3_adjudications?: number
    layer2_mrw_candidates?: number
    layer3_mipvu_tokens?: number
    [k: string]: unknown
  }
  wsd?: {
    enabled?: boolean
    applied_tokens?: number
    model_dir?: string | null
    fallback_reason?: string
    [k: string]: unknown
  }
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
  basic_meaning?: string
  source_domain_label?: string
  layer1_source?: string
  layer1_confidence?: number
  layer1_rationale?: string
  mrw_distance?: number
  mrw_similarity?: number
  mrw_method?: string
  is_metaphor_candidate?: boolean
  is_metaphor?: boolean
  mipvu_path?: string
  target_domain?: string
  target_domain_label?: string
  source_domain?: string
  confidence?: string
  mipvu_source_domain_label?: string
  mipvu_target_domain_label?: string
  mipvu?: {
    A?: { step?: string; decision?: string; reason?: string; [k: string]: unknown }
    B?: { step?: string; decision?: string; source_domain_label?: string; reason?: string; [k: string]: unknown }
    C?: { step?: string; target_domain_label?: string; free_description?: string; reason?: string; [k: string]: unknown }
    [k: string]: unknown
  }
  [k: string]: unknown
}

export type ProfileRow = {
  domain_code: string
  domain_label?: string
  label?: string
  count?: number
  frequency?: number
  relative_per_10k?: number
  tokens?: number
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
