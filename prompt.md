好，我来写一个完整的系统设计prompt，让Cursor从零构建整个pipeline。

---

````
# Build: Japanese MIPVU Metaphor Analysis System

## Project Overview
Build a Japanese MIPVU (Metaphor Identification Procedure Vrije Universiteit)
implementation that identifies metaphorical word usages and annotates both
source domain and target domain using USAS semantic tags.

Final output for each content word:
```json
{
  "word": "刃",
  "lemma": "刃",
  "pos": "名詞",
  "is_mrw": true,
  "source_domain": "K5.1",
  "source_domain_label": "武器・刃物",
  "target_domain": "E4.1",
  "target_domain_label": "感情・心理的影響",
  "basic_meaning": "blade of a sword or knife",
  "context_meaning": "sharp hurtful words",
  "mrw_distance": 0.71,
  "confidence": "high",
  "path": "wordnet+llm"
}
```

---

## Tech Stack

```
Python 3.10+
├── sudachipy + sudachidict_full    # Japanese tokenizer
├── transformers                    # BERT embeddings
│   └── tohoku-nlp/bert-base-japanese-v3
├── torch                           # tensor ops
├── llama-cpp-python                # local LLM (optional offline mode)
├── openai                          # OpenAI / DeepSeek / any OpenAI-compatible API
├── google-generativeai             # Gemini API
├── anthropic                       # Claude API
├── fastapi + uvicorn               # backend API server
├── sqlite3                         # cache + annotation store (built-in)
└── pytest                          # tests
```

---

## Directory Structure

```
mipvu_ja/
├── config/
│   └── settings.py          # API keys, model selection, thresholds
├── data/
│   ├── jmdict_usas.json     # JMdict→USAS static dict (pre-built)
│   ├── usas_labels_ja.json  # USAS tag → Japanese description
│   └── cache.db             # SQLite cache for LLM calls
├── core/
│   ├── tokenizer.py         # SudachiPy wrapper
│   ├── dictionary.py        # JMdict lookup
│   ├── embeddings.py        # BERT contextual embeddings
│   ├── usas_mapper.py       # keyword→USAS classification
│   └── mrw_detector.py      # cosine distance MRW detection
├── llm/
│   ├── base.py              # abstract LLMClient interface
│   ├── openai_client.py     # OpenAI + DeepSeek (same API format)
│   ├── gemini_client.py     # Google Gemini
│   ├── anthropic_client.py  # Claude
│   ├── local_client.py      # llama-cpp-python (offline)
│   └── router.py            # LLM router with fallback chain
├── pipeline/
│   ├── annotator.py         # main pipeline orchestrator
│   ├── source_domain.py     # source domain identification
│   └── target_domain.py     # target domain identification
├── api/
│   └── server.py            # FastAPI server
├── tests/
│   └── test_pipeline.py
└── main.py                  # CLI entry point
```

---

## Step-by-Step Implementation

### STEP 1: config/settings.py

```python
# All configuration in one place
# Users edit only this file

LLM_PROVIDER = "deepseek"  # "deepseek" | "openai" | "gemini" | "claude" | "local"

API_KEYS = {
    "deepseek":  "sk-...",
    "openai":    "sk-...",
    "gemini":    "...",
    "anthropic": "sk-ant-...",
}

# LLM fallback chain: try in order until one succeeds
LLM_FALLBACK_CHAIN = ["deepseek", "openai", "gemini", "claude", "local"]

# Local model path (used when provider="local" or all APIs fail)
LOCAL_MODEL_PATH = "./models/qwen3-4b-q4_k_m.gguf"

# MRW detection thresholds by POS
MRW_THRESHOLDS = {
    "名詞-サ変可能": 0.45,
    "名詞":          0.35,
    "動詞":          0.25,
    "形容詞":        0.28,
    "副詞":          0.30,
    "default":       0.35,
}

# Only annotate these POS
TARGET_POS = ["名詞", "動詞", "形容詞", "副詞"]

# BERT model
BERT_MODEL = "tohoku-nlp/bert-base-japanese-v3"

# SQLite cache path
CACHE_DB = "./data/cache.db"
```

---

### STEP 2: data/usas_labels_ja.json

Create this file with ALL standard USAS tags and Japanese descriptions:
```json
{
  "A1.1+": "一般的・肯定的評価",
  "A1.1-": "一般的・否定的評価",
  "A1.2": "重要性",
  "A1.5+": "有用性・便利さ",
  "A1.5-": "有害性・危険性",
  "A1.6+": "成功・達成",
  "A1.6-": "失敗・未達成",
  "A1.7": "真実・虚偽",
  "A1.8+": "予測可能・確実",
  "A1.8-": "予測不可能・不確実",
  "A1.9": "技術・方法",
  "A2.1": "変化・出来事・行為",
  "A2.2": "発生・発展",
  "A3": "時間的側面",
  "A4.1": "確かさ・可能性",
  "A4.2": "考え・提案",
  "A5.1": "試み・追求",
  "A5.2": "助力・妨害",
  "A6.1+": "存在・現実",
  "A6.1-": "非存在・不在",
  "A6.2": "所有・所属",
  "A6.3": "包含・除外",
  "A7": "程度・強度",
  "A8+": "関係性・類似",
  "A8-": "対立・差異",
  "A9+": "結合・連結",
  "A9-": "分離・切断",
  "A10+": "整序・調和",
  "A10-": "混乱・無秩序",
  "A11+": "開始・前置き",
  "A11-": "終了・後続",
  "A12": "目的・目標",
  "A13+": "使用・機能",
  "A13-": "不使用・機能不全",
  "A14": "状態・条件",
  "B1": "身体・解剖",
  "B2": "健康・疾病",
  "B3": "食事・栄養",
  "B4": "性・出産・生殖",
  "B5": "死・生存",
  "C1": "芸術・文化・娯楽",
  "E1": "感情全般",
  "E2": "感情表出",
  "E3": "怒り・恐怖",
  "E4.1": "ポジティブ感情・喜び",
  "E4.2": "ネガティブ感情・悲しみ",
  "E5": "驚き・意外",
  "E6": "満足・不満",
  "F1": "食べ物・飲み物",
  "F2": "農業・農村",
  "F3": "環境・生態",
  "F4": "動物全般",
  "G1.1": "政府・行政",
  "G1.2": "法律・規則",
  "G2": "軍事・戦争",
  "G3": "外交・国際関係",
  "H1": "建築・建物",
  "H2": "家庭・家族",
  "H3": "家事・日常生活",
  "H4": "職業・仕事全般",
  "H5": "産業・製造",
  "I1": "企業・組織・会社",
  "I1.1": "金融・経済",
  "I1.2": "商業・貿易",
  "I1.3": "生産・製造",
  "I2": "教育・学習",
  "I3": "通信・情報技術",
  "I3.1": "コンピュータ・IT",
  "I4": "科学・技術",
  "K1": "音楽",
  "K2": "視覚芸術",
  "K3": "演劇・映画",
  "K4": "文学・書籍",
  "K5.1": "スポーツ・競技",
  "K5.2": "競技成績・勝敗・順位",
  "K6": "趣味・余暇",
  "L1": "生命・生物",
  "L2": "植物",
  "L3": "動物",
  "M1": "移動・交通",
  "M2": "道路・経路",
  "M3": "乗り物",
  "M4": "航空",
  "M5": "船舶",
  "M6": "鉄道",
  "M7": "インフラ・建設",
  "M8": "地理・場所",
  "N1": "数・量",
  "N2": "数学・計算",
  "N3": "測定・単位",
  "N4": "順序・順番",
  "N5": "統計・確率",
  "N6": "大きさ・程度",
  "O1": "言語・言語学",
  "O2": "名称・呼称",
  "O3": "色・形",
  "O4": "音・音声",
  "P1": "教育・学校",
  "P1.1": "学術・研究",
  "P1.2": "宗教・信仰",
  "Q1.1": "コミュニケーション全般",
  "Q1.2": "話す・言う",
  "Q1.3": "書く・記録",
  "Q2": "メディア・出版",
  "Q2.1": "新聞・ニュース",
  "Q2.2": "放送・テレビ",
  "Q3": "音楽・楽器",
  "Q4": "電気通信",
  "R": "宗教・信仰",
  "S1.1": "対人関係・社会的役割",
  "S1.2": "男女関係",
  "S1.3": "家族関係",
  "S2": "人・人物",
  "S3": "人の属性",
  "S4": "道徳・倫理",
  "S5+": "組織・団体・機関",
  "S6": "文化・社会規範",
  "S7": "犯罪・違法行為",
  "S7.1": "警察・司法",
  "S7.2": "刑罰・矯正",
  "S7.3+": "誠実・正直",
  "S7.3-": "不誠実・欺瞞",
  "S7.4+": "自由・権利",
  "S7.4-": "抑圧・束縛",
  "S8+": "礼儀・敬意",
  "S8-": "無礼・軽蔑",
  "S9": "宗教的・精神的実践",
  "T1.1": "時間全般",
  "T1.1.1": "過去",
  "T1.1.2": "現在",
  "T1.1.3": "未来",
  "T1.2": "時刻・時間帯",
  "T1.3": "持続・継続",
  "T2": "新旧・変化",
  "T3": "速度・頻度",
  "T4": "段階・順序",
  "W1": "世界・宇宙",
  "W2": "自然環境",
  "W3": "地形・地理",
  "W4": "天気・気候",
  "W5": "元素・物質",
  "X1": "一般的精神活動",
  "X2.1": "知識・理解・思考",
  "X2.2": "評価・判断",
  "X3": "反省・内省",
  "X4": "希望・欲求",
  "X5": "夢・想像",
  "X6": "記憶・想起",
  "X7": "発見・学習",
  "X8": "信念・意見",
  "X9": "注意・意識",
  "Y1": "情報・データ",
  "Y2": "記録・文書",
  "Z1": "名詞句（内容語なし）",
  "Z2": "名前・固有名詞",
  "Z3": "地名",
  "Z4": "略語",
  "Z5": "文法語・機能語",
  "Z6": "感嘆詞",
  "Z7": "代名詞",
  "Z8": "存在を示す語",
  "Z99": "未分類・不明"
}
```

---

### STEP 3: core/tokenizer.py

```python
"""SudachiPy wrapper with POS filtering."""
import sudachipy
import sudachidict_full
from dataclasses import dataclass

@dataclass
class Token:
    surface: str
    lemma: str
    pos: str           # e.g. "名詞"
    pos_detail: str    # e.g. "名詞-サ変可能"
    reading: str

class JapaneseTokenizer:
    def __init__(self):
        self.tokenizer = sudachipy.Dictionary().create()
        self.mode = sudachipy.SplitMode.C  # use longest match

    def tokenize(self, text: str, pos_filter: list[str] = None) -> list[Token]:
        morphemes = self.tokenizer.tokenize(text, self.mode)
        tokens = []
        for m in morphemes:
            pos_parts = m.part_of_speech()
            pos_main = pos_parts[0]
            pos_sub = pos_parts[2] if len(pos_parts) > 2 else ""
            pos_detail = f"{pos_main}-{pos_sub}" if pos_sub and pos_sub != "*" else pos_main

            token = Token(
                surface=m.surface(),
                lemma=m.dictionary_form(),
                pos=pos_main,
                pos_detail=pos_detail,
                reading=m.reading_form(),
            )
            if pos_filter is None or pos_main in pos_filter:
                tokens.append(token)
        return tokens
```

---

### STEP 4: core/dictionary.py

```python
"""
JMdict + USAS static dictionary lookup.
Loads jmdict_usas.json built by the separate build_dict.py script.
"""
import json
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DictEntry:
    lemma: str
    basic_meaning: str   # English gloss from JMdict
    usas_tag: str        # pre-mapped USAS tag
    source: str          # "jmdict_usas" | "z99_fallback"

class JMdictUSASLookup:
    def __init__(self, dict_path: str = "./data/jmdict_usas.json"):
        path = Path(dict_path)
        if not path.exists():
            raise FileNotFoundError(
                f"jmdict_usas.json not found at {dict_path}.\n"
                "Please run: python build_dict.py first."
            )
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # data format: {"lemma": {"meaning": "...", "usas": "K5.2"}, ...}
        self.dict = data

    def lookup(self, lemma: str) -> DictEntry | None:
        entry = self.dict.get(lemma)
        if entry:
            return DictEntry(
                lemma=lemma,
                basic_meaning=entry.get("meaning", ""),
                usas_tag=entry.get("usas", "Z99"),
                source="jmdict_usas",
            )
        return None

    def lookup_with_fallback(self, lemma: str, reading: str = None) -> DictEntry:
        # Try lemma first
        result = self.lookup(lemma)
        if result:
            return result
        # Try reading form
        if reading:
            result = self.lookup(reading)
            if result:
                return result
        # Try compound head (last 2 chars) for OOV
        if len(lemma) >= 2:
            head = lemma[-2:]
            result = self.lookup(head)
            if result:
                return DictEntry(
                    lemma=lemma,
                    basic_meaning=f"(compound) {result.basic_meaning}",
                    usas_tag=result.usas_tag,
                    source="compound_head",
                )
        return DictEntry(
            lemma=lemma,
            basic_meaning="",
            usas_tag="Z99",
            source="z99_fallback",
        )
```

---

### STEP 5: core/embeddings.py

```python
"""
BERT contextual embeddings for MRW detection.
Computes cosine distance between basic-meaning context
and in-sentence context to detect semantic shift.
"""
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from config.settings import BERT_MODEL

class BERTEmbedder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL)
        self.model = AutoModel.from_pretrained(BERT_MODEL)
        self.model.eval()

    def _get_embedding(self, text: str, target_word: str = None) -> np.ndarray:
        """
        Get sentence-level embedding.
        If target_word given, attempts to extract that word's token embedding.
        Falls back to CLS token.
        """
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding=True,
        )
        with torch.no_grad():
            outputs = self.model(**inputs)

        # Try to locate target word tokens
        if target_word:
            target_ids = self.tokenizer(
                target_word,
                add_special_tokens=False
            )["input_ids"]
            input_ids = inputs["input_ids"][0].tolist()
            # Find subword position
            for i in range(len(input_ids) - len(target_ids) + 1):
                if input_ids[i:i+len(target_ids)] == target_ids:
                    word_vecs = outputs.last_hidden_state[0, i:i+len(target_ids)]
                    return word_vecs.mean(dim=0).numpy()

        # Fallback: CLS token
        return outputs.last_hidden_state[0, 0].numpy()

    def cosine_distance(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8)
        return float(1.0 - sim)

    def compute_mrw_distance(
        self,
        lemma: str,
        basic_meaning: str,
        sentence: str,
    ) -> float:
        """
        Distance between word's basic meaning context
        and its in-sentence context.
        Higher = more likely metaphorical.
        """
        if not basic_meaning:
            return 0.0
        vec_basic = self._get_embedding(basic_meaning, lemma)
        vec_context = self._get_embedding(sentence, lemma)
        return self.cosine_distance(vec_basic, vec_context)
```

---

### STEP 6: core/mrw_detector.py

```python
"""MRW (Metaphor Related Word) detection using BERT distance + POS-aware thresholds."""
from config.settings import MRW_THRESHOLDS
from core.embeddings import BERTEmbedder
from core.tokenizer import Token

class MRWDetector:
    def __init__(self, embedder: BERTEmbedder):
        self.embedder = embedder

    def get_threshold(self, token: Token) -> float:
        return (
            MRW_THRESHOLDS.get(token.pos_detail)
            or MRW_THRESHOLDS.get(token.pos)
            or MRW_THRESHOLDS["default"]
        )

    def detect(
        self,
        token: Token,
        basic_meaning: str,
        sentence: str,
    ) -> tuple[bool, float]:
        """
        Returns (is_mrw_candidate, distance_score)
        """
        distance = self.embedder.compute_mrw_distance(
            token.lemma, basic_meaning, sentence
        )
        threshold = self.get_threshold(token)
        is_candidate = distance >= threshold
        return is_candidate, distance
```

---

### STEP 7: llm/base.py

```python
"""Abstract interface for all LLM clients."""
from abc import ABC, abstractmethod

class LLMClient(ABC):
    """All LLM clients must implement this interface."""

    @abstractmethod
    def classify_source_domain(
        self,
        word: str,
        basic_meaning: str,
        candidates: list[tuple[str, str]],  # [(tag, ja_description), ...]
    ) -> str:
        """Choose best USAS tag from candidates. Returns tag string."""
        pass

    @abstractmethod
    def confirm_mrw(
        self,
        word: str,
        basic_meaning: str,
        sentence: str,
    ) -> bool:
        """Confirm if word is used metaphorically in sentence."""
        pass

    @abstractmethod
    def identify_target_domain(
        self,
        word: str,
        sentence: str,
        source_tag: str,
        all_tags: dict[str, str],  # {tag: ja_description}
    ) -> str:
        """Identify target domain USAS tag from context."""
        pass
```

---

### STEP 8: llm/openai_client.py

```python
"""
OpenAI-compatible client.
Works for: OpenAI, DeepSeek, any OpenAI-compatible API.
DeepSeek base URL: https://api.deepseek.com/v1
"""
from openai import OpenAI
from llm.base import LLMClient

class OpenAICompatibleClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,  # None = default OpenAI endpoint
        )
        self.model = model

    def _chat(self, prompt: str, max_tokens: int = 10) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()

    def classify_source_domain(self, word, basic_meaning, candidates):
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""日本語の語「{word}」の基本的な意味は「{basic_meaning}」です。
この語の「源領域（source domain）」として最も適切なUSASカテゴリを選んでください。

選択肢：
{options}

選択肢の記号（A, B, C...）を一文字だけ回答してください："""

        choice = self._chat(prompt, max_tokens=3).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        if 0 <= idx < len(candidates):
            return candidates[idx][0]
        return candidates[0][0]

    def confirm_mrw(self, word, basic_meaning, sentence):
        prompt = f"""以下の文で「{word}」が比喩的（隠喩的）に使われているかを判定してください。

語の基本的な意味：{basic_meaning}
文：「{sentence}」

この文での「{word}」は基本的な意味とは異なる概念領域を指しますか？
「はい」か「いいえ」のみで回答してください："""

        answer = self._chat(prompt, max_tokens=5)
        return "はい" in answer or "yes" in answer.lower()

    def identify_target_domain(self, word, sentence, source_tag, all_tags):
        # Select top candidate tags to present (exclude source tag, limit to 8)
        candidates = [
            (tag, desc) for tag, desc in all_tags.items()
            if tag != source_tag and not tag.startswith("Z")
        ][:8]
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""以下の文で「{word}」は比喩的に使われています。
この語が「目標領域（target domain）」として指し示している概念は何ですか？

文：「{sentence}」
源領域（この語の字義的カテゴリ）：[{source_tag}]

目標領域として最も適切なものを選んでください：
{options}

選択肢の記号（A, B, C...）を一文字だけ回答してください："""

        choice = self._chat(prompt, max_tokens=3).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        if 0 <= idx < len(candidates):
            return candidates[idx][0]
        return "Z99"
```

---

### STEP 9: llm/gemini_client.py

```python
"""Google Gemini client."""
import google.generativeai as genai
from llm.base import LLMClient
from llm.openai_client import OpenAICompatibleClient

class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def _chat(self, prompt: str) -> str:
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=10,
                temperature=0.0,
            )
        )
        return response.text.strip()

    # Reuse the same prompt logic as OpenAI client
    def classify_source_domain(self, word, basic_meaning, candidates):
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""日本語の語「{word}」の基本的な意味は「{basic_meaning}」です。
源領域のUSASカテゴリを一文字（A/B/C...）で選んでください：
{options}
回答："""
        choice = self._chat(prompt).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        return candidates[idx][0] if 0 <= idx < len(candidates) else candidates[0][0]

    def confirm_mrw(self, word, basic_meaning, sentence):
        prompt = f"""「{sentence}」における「{word}」（基本義：{basic_meaning}）は比喩的ですか？「はい」か「いいえ」："""
        return "はい" in self._chat(prompt)

    def identify_target_domain(self, word, sentence, source_tag, all_tags):
        candidates = [
            (tag, desc) for tag, desc in all_tags.items()
            if tag != source_tag and not tag.startswith("Z")
        ][:8]
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""「{sentence}」で比喩的に使われた「{word}」の目標領域を一文字で選んでください：
{options}
回答："""
        choice = self._chat(prompt).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        return candidates[idx][0] if 0 <= idx < len(candidates) else "Z99"
```

---

### STEP 10: llm/anthropic_client.py

```python
"""Claude (Anthropic) client."""
import anthropic
from llm.base import LLMClient

class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _chat(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def classify_source_domain(self, word, basic_meaning, candidates):
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""「{word}」（基本義：{basic_meaning}）の源領域USASカテゴリを一文字で：
{options}
回答："""
        choice = self._chat(prompt).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        return candidates[idx][0] if 0 <= idx < len(candidates) else candidates[0][0]

    def confirm_mrw(self, word, basic_meaning, sentence):
        prompt = f"""「{sentence}」の「{word}」（基本義：{basic_meaning}）は比喩的？「はい」か「いいえ」："""
        return "はい" in self._chat(prompt)

    def identify_target_domain(self, word, sentence, source_tag, all_tags):
        candidates = [
            (tag, desc) for tag, desc in all_tags.items()
            if tag != source_tag and not tag.startswith("Z")
        ][:8]
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""「{sentence}」で「{word}」の目標領域を一文字で：
{options}
回答："""
        choice = self._chat(prompt).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        return candidates[idx][0] if 0 <= idx < len(candidates) else "Z99"
```

---

### STEP 11: llm/local_client.py

```python
"""Local LLM via llama-cpp-python (offline fallback)."""
from llm.base import LLMClient
from config.settings import LOCAL_MODEL_PATH

class LocalLLMClient(LLMClient):
    def __init__(self):
        try:
            from llama_cpp import Llama
            self.llm = Llama(
                model_path=LOCAL_MODEL_PATH,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load local model from {LOCAL_MODEL_PATH}.\n"
                f"Download a GGUF model and set LOCAL_MODEL_PATH in settings.py.\n"
                f"Error: {e}"
            )

    def _chat(self, prompt: str) -> str:
        response = self.llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5,
            temperature=0.0,
            stop=["\n", "。", ".", " "],
        )
        return response["choices"][0]["message"]["content"].strip()

    # Same prompt structure as other clients
    def classify_source_domain(self, word, basic_meaning, candidates):
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""「{word}」（意味：{basic_meaning}）の源領域を一文字で選択：
{options}
回答："""
        choice = self._chat(prompt).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        return candidates[idx][0] if 0 <= idx < len(candidates) else candidates[0][0]

    def confirm_mrw(self, word, basic_meaning, sentence):
        prompt = f"""「{word}」は「{sentence}」で比喩的か？はい/いいえ："""
        return "はい" in self._chat(prompt)

    def identify_target_domain(self, word, sentence, source_tag, all_tags):
        candidates = [
            (tag, desc) for tag, desc in all_tags.items()
            if tag != source_tag and not tag.startswith("Z")
        ][:6]
        options = "\n".join(
            f"{chr(65+i)}. [{tag}] {desc}"
            for i, (tag, desc) in enumerate(candidates)
        )
        prompt = f"""「{word}」（「{sentence}」）の目標領域を一文字で：
{options}
回答："""
        choice = self._chat(prompt).upper()
        idx = ord(choice[0]) - 65 if choice and choice[0].isalpha() else 0
        return candidates[idx][0] if 0 <= idx < len(candidates) else "Z99"
```

---

### STEP 12: llm/router.py

```python
"""
LLM router with fallback chain + SQLite caching.
Tries providers in order until one succeeds.
Caches results to avoid redundant API calls.
"""
import sqlite3
import json
import hashlib
from llm.base import LLMClient
from config.settings import (
    API_KEYS, LLM_FALLBACK_CHAIN, LLM_PROVIDER, CACHE_DB
)

def build_client(provider: str) -> LLMClient:
    key = API_KEYS.get(provider, "")
    if provider == "deepseek":
        from llm.openai_client import OpenAICompatibleClient
        return OpenAICompatibleClient(
            api_key=key,
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
        )
    elif provider == "openai":
        from llm.openai_client import OpenAICompatibleClient
        return OpenAICompatibleClient(api_key=key, model="gpt-4o-mini")
    elif provider == "gemini":
        from llm.gemini_client import GeminiClient
        return GeminiClient(api_key=key)
    elif provider == "claude":
        from llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=key)
    elif provider == "local":
        from llm.local_client import LocalLLMClient
        return LocalLLMClient()
    else:
        raise ValueError(f"Unknown provider: {provider}")

class LLMRouter:
    def __init__(self):
        self._init_cache()
        # Build client list: primary first, then fallback chain
        chain = [LLM_PROVIDER] + [
            p for p in LLM_FALLBACK_CHAIN if p != LLM_PROVIDER
        ]
        self.clients: list[tuple[str, LLMClient]] = []
        for provider in chain:
            try:
                client = build_client(provider)
                self.clients.append((provider, client))
            except Exception:
                pass  # skip unavailable providers

    def _init_cache(self):
        self.conn = sqlite3.connect(CACHE_DB)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                key TEXT PRIMARY KEY,
                result TEXT,
                provider TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def _cache_key(self, method: str, **kwargs) -> str:
        content = json.dumps({"method": method, **kwargs}, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache(self, key: str):
        row = self.conn.execute(
            "SELECT result FROM llm_cache WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def _set_cache(self, key: str, result: str, provider: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO llm_cache (key, result, provider) VALUES (?,?,?)",
            (key, result, provider)
        )
        self.conn.commit()

    def _call_with_fallback(self, method_name: str, cache_key: str, **kwargs):
        # Check cache first
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Try each provider in order
        last_error = None
        for provider_name, client in self.clients:
            try:
                method = getattr(client, method_name)
                result = method(**kwargs)
                self._set_cache(cache_key, str(result), provider_name)
                return result
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            f"All LLM providers failed for {method_name}. Last error: {last_error}"
        )

    def classify_source_domain(self, word, basic_meaning, candidates):
        key = self._cache_key("classify_source_domain",
                               word=word, meaning=basic_meaning)
        return self._call_with_fallback(
            "classify_source_domain", key,
            word=word, basic_meaning=basic_meaning, candidates=candidates
        )

    def confirm_mrw(self, word, basic_meaning, sentence):
        key = self._cache_key("confirm_mrw",
                               word=word, sentence=sentence)
        result = self._call_with_fallback(
            "confirm_mrw", key,
            word=word, basic_meaning=basic_meaning, sentence=sentence
        )
        return result == "True" or result is True

    def identify_target_domain(self, word, sentence, source_tag, all_tags):
        key = self._cache_key("identify_target_domain",
                               word=word, sentence=sentence, src=source_tag)
        return self._call_with_fallback(
            "identify_target_domain", key,
            word=word, sentence=sentence,
            source_tag=source_tag, all_tags=all_tags
        )
```

---

### STEP 13: pipeline/annotator.py

```python
"""
Main MIPVU annotation pipeline.
Orchestrates all layers for each token.
"""
import json
from dataclasses import dataclass, asdict
from core.tokenizer import JapaneseTokenizer, Token
from core.dictionary import JMdictUSASLookup
from core.embeddings import BERTEmbedder
from core.mrw_detector import MRWDetector
from llm.router import LLMRouter
from config.settings import TARGET_POS

@dataclass
class TokenAnnotation:
    word: str
    lemma: str
    pos: str
    is_mrw: bool
    source_domain: str
    source_domain_label: str
    target_domain: str | None
    target_domain_label: str | None
    basic_meaning: str
    mrw_distance: float
    confidence: str   # "high" | "medium" | "low"
    path: str         # which layers were used

class MIPVUAnnotator:
    def __init__(self):
        self.tokenizer = JapaneseTokenizer()
        self.dictionary = JMdictUSASLookup()
        self.embedder = BERTEmbedder()
        self.mrw_detector = MRWDetector(self.embedder)
        self.llm = LLMRouter()

        # Load USAS label descriptions
        with open("./data/usas_labels_ja.json", encoding="utf-8") as f:
            self.usas_labels: dict[str, str] = json.load(f)

    def _get_source_candidates(self, usas_tag: str) -> list[tuple[str, str]]:
        """
        Build candidate list for source domain classification.
        Returns top candidates centered around the pre-mapped tag.
        """
        # Always include the pre-mapped tag
        candidates = [(usas_tag, self.usas_labels.get(usas_tag, usas_tag))]

        # Add semantically adjacent tags (same top-level category)
        prefix = usas_tag[0]
        neighbors = [
            (tag, desc) for tag, desc in self.usas_labels.items()
            if tag.startswith(prefix) and tag != usas_tag
        ][:4]
        candidates.extend(neighbors)

        # Always include Z99 as last option
        if ("Z99", self.usas_labels["Z99"]) not in candidates:
            candidates.append(("Z99", self.usas_labels["Z99"]))

        return candidates

    def annotate_token(
        self,
        token: Token,
        sentence: str,
    ) -> TokenAnnotation:
        # Layer 1: Dictionary lookup
        entry = self.dictionary.lookup_with_fallback(token.lemma, token.reading)

        # Layer 2: BERT MRW detection
        is_mrw_candidate, distance = self.mrw_detector.detect(
            token, entry.basic_meaning, sentence
        )

        # Determine path and confidence
        path_parts = [entry.source]

        if not is_mrw_candidate:
            # Not metaphorical: source domain = pre-mapped tag, no target domain
            return TokenAnnotation(
                word=token.surface,
                lemma=token.lemma,
                pos=token.pos,
                is_mrw=False,
                source_domain=entry.usas_tag,
                source_domain_label=self.usas_labels.get(entry.usas_tag, ""),
                target_domain=None,
                target_domain_label=None,
                basic_meaning=entry.basic_meaning,
                mrw_distance=round(distance, 4),
                confidence="high" if entry.source == "jmdict_usas" else "low",
                path="+".join(path_parts),
            )

        # Layer 3a: LLM confirms MRW
        path_parts.append("bert")
        is_confirmed_mrw = self.llm.confirm_mrw(
            token.lemma, entry.basic_meaning, sentence
        )
        path_parts.append("llm_mrw")

        if not is_confirmed_mrw:
            return TokenAnnotation(
                word=token.surface,
                lemma=token.lemma,
                pos=token.pos,
                is_mrw=False,
                source_domain=entry.usas_tag,
                source_domain_label=self.usas_labels.get(entry.usas_tag, ""),
                target_domain=None,
                target_domain_label=None,
                basic_meaning=entry.basic_meaning,
                mrw_distance=round(distance, 4),
                confidence="medium",
                path="+".join(path_parts),
            )

        # Layer 3b: LLM refines source domain
        candidates = self._get_source_candidates(entry.usas_tag)
        source_tag = self.llm.classify_source_domain(
            token.lemma, entry.basic_meaning, candidates
        )
        path_parts.append("llm_src")

        # Layer 3c: LLM identifies target domain
        target_tag = self.llm.identify_target_domain(
            token.lemma, sentence, source_tag, self.usas_labels
        )
        path_parts.append("llm_tgt")

        return TokenAnnotation(
            word=token.surface,
            lemma=token.lemma,
            pos=token.pos,
            is_mrw=True,
            source_domain=source_tag,
            source_domain_label=self.usas_labels.get(source_tag, ""),
            target_domain=target_tag,
            target_domain_label=self.usas_labels.get(target_tag, ""),
            basic_meaning=entry.basic_meaning,
            mrw_distance=round(distance, 4),
            confidence="medium",
            path="+".join(path_parts),
        )

    def annotate(self, text: str) -> list[TokenAnnotation]:
        tokens = self.tokenizer.tokenize(text, pos_filter=TARGET_POS)
        return [self.annotate_token(t, text) for t in tokens]

    def annotate_to_dict(self, text: str) -> list[dict]:
        return [asdict(a) for a in self.annotate(text)]
```

---

### STEP 14: api/server.py

```python
"""FastAPI server exposing the annotation pipeline."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline.annotator import MIPVUAnnotator

app = FastAPI(title="MIPVU Japanese Annotator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

annotator = MIPVUAnnotator()

class AnnotateRequest(BaseModel):
    text: str

@app.post("/annotate")
async def annotate(req: AnnotateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is empty")
    try:
        results = annotator.annotate_to_dict(req.text)
        mrw_count = sum(1 for r in results if r["is_mrw"])
        return {
            "text": req.text,
            "token_count": len(results),
            "mrw_count": mrw_count,
            "annotations": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

### STEP 15: main.py

```python
"""CLI entry point."""
import json
import argparse
from pipeline.annotator import MIPVUAnnotator

def main():
    parser = argparse.ArgumentParser(description="MIPVU Japanese Annotator")
    parser.add_argument("text", nargs="?", help="Text to annotate")
    parser.add_argument("--file", help="Input text file")
    parser.add_argument("--output", default="output.json", help="Output JSON file")
    parser.add_argument("--serve", action="store_true", help="Start API server")
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        uvicorn.run("api.server:app", host="0.0.0.0", port=8765, reload=False)
        return

    annotator = MIPVUAnnotator()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = input("テキストを入力してください: ")

    results = annotator.annotate_to_dict(text)

    # Print summary
    mrw_words = [r for r in results if r["is_mrw"]]
    print(f"\n=== 分析結果 ===")
    print(f"トークン数: {len(results)}")
    print(f"MRW数: {len(mrw_words)}")
    print()
    for r in results:
        mrw_mark = "🔴" if r["is_mrw"] else "⚪"
        print(f"{mrw_mark} {r['word']} ({r['lemma']})")
        print(f"   源領域: [{r['source_domain']}] {r['source_domain_label']}")
        if r["is_mrw"]:
            print(f"   目標領域: [{r['target_domain']}] {r['target_domain_label']}")
        print(f"   距離: {r['mrw_distance']} | 経路: {r['path']}")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n→ {args.output} に保存しました")

if __name__ == "__main__":
    main()
```

---

### STEP 16: tests/test_pipeline.py

```python
"""Basic smoke tests."""
import pytest
from pipeline.annotator import MIPVUAnnotator

@pytest.fixture(scope="module")
def annotator():
    return MIPVUAnnotator()

def test_literal_usage(annotator):
    """準優勝 should NOT be MRW."""
    results = annotator.annotate("彼は大会で準優勝した。")
    junyu = next((r for r in results if r.lemma == "準優勝"), None)
    if junyu:
        assert junyu.source_domain != "Z99"
        assert junyu.is_mrw == False

def test_metaphor_detection(annotator):
    """刃 in emotional context should be MRW."""
    results = annotator.annotate("彼女の言葉は刃のように刺さった。")
    ha = next((r for r in results if r.lemma == "刃"), None)
    if ha:
        assert ha.is_mrw == True
        assert ha.source_domain in ["K5.1", "A1.5-", "W5"]
        assert ha.target_domain is not None

def test_no_crash_on_empty(annotator):
    results = annotator.annotate("の")
    assert isinstance(results, list)

def test_api_server():
    from fastapi.testclient import TestClient
    from api.server import app
    client = TestClient(app)
    resp = client.post("/annotate", json={"text": "山が高い。"})
    assert resp.status_code == 200
    data = resp.json()
    assert "annotations" in data
```

---

## Implementation Order for Cursor

Execute in this order:
1. Create directory structure
2. Implement settings.py — fill in at least one API key
3. Create usas_labels_ja.json (the full tag list above)
4. Implement core/ modules (tokenizer → dictionary → embeddings → mrw_detector)
5. Implement llm/ modules (base → openai → gemini → anthropic → local → router)
6. Implement pipeline/annotator.py
7. Implement api/server.py and main.py
8. Run tests: `pytest tests/ -v`
9. Smoke test: `python main.py "彼女の言葉は刃のように刺さった。"`

## Dependencies to install first

```bash
pip install sudachipy sudachidict_full
pip install transformers torch
pip install openai google-generativeai anthropic
pip install fastapi uvicorn pytest
pip install llama-cpp-python  # optional, for offline mode
```

## Notes for Cursor
- jmdict_usas.json must exist before running. If missing, tell the user
  to run build_dict.py first (separate script already built)
- The LLM layer (Steps 7-12) is ONLY called when BERT detects a
  metaphor candidate. Literal words never touch the API → low cost
- All LLM calls are multiple-choice, never free generation → no hallucination
- SQLite cache means repeated identical inputs never re-call the API
- If all API providers fail AND no local model exists, the system
  falls back gracefully: is_mrw stays True but target_domain = "Z99"
````

---

把这整段贴给Cursor的Agent模式，它会按顺序建目录、写文件、安装依赖。唯一需要你手动做的是在`settings.py`里填入至少一个API key，然后确认`jmdict_usas.json`已经由之前的build_dict.py生成好了。