export async function apiAnalyze(payload) {
  return window.pywebview.api.analyze(payload);
}

export async function apiBootstrap() {
  return window.pywebview.api.bootstrap();
}

export async function apiDomainWords(domainCode) {
  return window.pywebview.api.domain_words(domainCode);
}

export async function apiKwic(keyword, domainCode) {
  return window.pywebview.api.kwic(keyword, domainCode);
}

export async function apiLexiconOverview() {
  return window.pywebview.api.lexicon_overview();
}

export async function apiAddLexiconTerms(payload) {
  return window.pywebview.api.add_lexicon_terms(payload);
}
