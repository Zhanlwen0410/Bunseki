from __future__ import annotations

import argparse
import json
import re
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


RULES = [
    {
        "name": "SPORT_COMPETITION",
        "keywords": [
            "champion",
            "runner-up",
            "tournament",
            "victory",
            "defeat",
            "score",
            "rank",
            "medal",
            "prize",
            "finalist",
            "semifinal",
            "playoff",
            "league",
            "cup",
            "title",
            "podium",
            "win",
            "winner",
        ],
        "tag": "K5.2",
    },
    {
        "name": "SPORT_GENERAL",
        "keywords": [
            "sport",
            "athlete",
            "player",
            "game",
            "match",
            "team",
            "coach",
            "training",
            "exercise",
            "gym",
            "stadium",
            "baseball",
            "soccer",
            "tennis",
            "swimming",
            "running",
            "soccer player",
        ],
        "tag": "K5.1",
    },
    {
        "name": "BODY",
        "keywords": [
            "body",
            "hand",
            "eye",
            "heart",
            "head",
            "face",
            "arm",
            "leg",
            "blood",
            "bone",
            "skin",
            "organ",
            "muscle",
            "stomach",
            "brain",
            "nerve",
            "cell",
        ],
        "tag": "B1",
    },
    {
        "name": "HEALTH_ILLNESS",
        "keywords": [
            "sick",
            "ill",
            "disease",
            "pain",
            "symptom",
            "injury",
            "wound",
            "cure",
            "heal",
            "medicine",
            "treatment",
            "hospital",
            "doctor",
            "patient",
            "surgery",
            "therapy",
            "drug",
        ],
        "tag": "B2",
    },
    {
        "name": "EMOTION",
        "keywords": [
            "happy",
            "sad",
            "angry",
            "fear",
            "love",
            "hate",
            "emotion",
            "feeling",
            "mood",
            "anxiety",
            "joy",
            "grief",
            "surprise",
            "shame",
            "pride",
            "envy",
            "hope",
            "despair",
        ],
        "tag": "E4.1",
    },
    {
        "name": "MENTAL_PROCESS",
        "keywords": [
            "think",
            "know",
            "understand",
            "believe",
            "remember",
            "forget",
            "imagine",
            "decide",
            "judge",
            "perceive",
            "realize",
            "recognize",
            "consider",
            "assume",
        ],
        "tag": "X2.1",
    },
    {
        "name": "LANGUAGE_COMM",
        "keywords": [
            "word",
            "language",
            "speech",
            "talk",
            "say",
            "speak",
            "write",
            "read",
            "text",
            "message",
            "letter",
            "sentence",
            "grammar",
            "vocabulary",
            "pronunciation",
            "conversation",
        ],
        "tag": "Q1.2",
    },
    {
        "name": "SOCIAL_RELATION",
        "keywords": [
            "friend",
            "colleague",
            "partner",
            "rival",
            "relationship",
            "bond",
            "trust",
            "respect",
            "conflict",
            "cooperate",
            "family",
            "parent",
            "child",
            "sibling",
            "marriage",
        ],
        "tag": "S1.1",
    },
    {
        "name": "ORGANIZATION",
        "keywords": [
            "company",
            "organization",
            "government",
            "school",
            "university",
            "hospital",
            "institution",
            "group",
            "party",
            "association",
            "ministry",
            "department",
            "agency",
            "committee",
            "union",
        ],
        "tag": "S5+",
    },
    {
        "name": "MONEY_FINANCE",
        "keywords": [
            "money",
            "price",
            "cost",
            "pay",
            "earn",
            "profit",
            "loss",
            "tax",
            "budget",
            "finance",
            "economy",
            "trade",
            "market",
            "salary",
            "wage",
            "bank",
            "investment",
            "debt",
        ],
        "tag": "I1.1",
    },
    {
        "name": "FOOD_DRINK",
        "keywords": [
            "food",
            "eat",
            "drink",
            "cook",
            "meal",
            "rice",
            "meat",
            "fish",
            "vegetable",
            "fruit",
            "soup",
            "bread",
            "taste",
            "flavor",
            "restaurant",
            "kitchen",
        ],
        "tag": "F1",
    },
    {
        "name": "NATURE_GEOGRAPHY",
        "keywords": [
            "mountain",
            "river",
            "sea",
            "ocean",
            "forest",
            "lake",
            "island",
            "valley",
            "plain",
            "coast",
            "desert",
            "jungle",
            "earth",
            "land",
            "ground",
            "soil",
        ],
        "tag": "W3",
    },
    {
        "name": "WEATHER",
        "keywords": [
            "weather",
            "rain",
            "snow",
            "wind",
            "sun",
            "cloud",
            "storm",
            "thunder",
            "fog",
            "temperature",
            "cold",
            "hot",
            "humid",
            "dry",
            "season",
            "climate",
        ],
        "tag": "W4",
    },
    {
        "name": "TIME",
        "keywords": [
            "time",
            "moment",
            "period",
            "age",
            "era",
            "season",
            "year",
            "month",
            "week",
            "day",
            "hour",
            "minute",
            "past",
            "present",
            "future",
            "ancient",
            "modern",
        ],
        "tag": "T1.1",
    },
    {
        "name": "MOVEMENT_TRANSPORT",
        "keywords": [
            "move",
            "travel",
            "transport",
            "vehicle",
            "car",
            "train",
            "ship",
            "plane",
            "road",
            "path",
            "journey",
            "trip",
            "arrive",
            "depart",
            "carry",
            "deliver",
            "run",
            "walk",
            "go",
            "come",
        ],
        "tag": "M1",
    },
    {
        "name": "PLACE_LOCATION",
        "keywords": [
            "place",
            "location",
            "area",
            "region",
            "district",
            "street",
            "building",
            "house",
            "room",
            "floor",
            "position",
            "address",
            "near",
            "far",
            "inside",
            "outside",
        ],
        "tag": "M7",
    },
    {
        "name": "NUMBER_QUANTITY",
        "keywords": [
            "number",
            "amount",
            "quantity",
            "count",
            "measure",
            "size",
            "large",
            "small",
            "many",
            "few",
            "total",
            "ratio",
            "percent",
            "degree",
            "level",
            "rate",
        ],
        "tag": "N2",
    },
    {
        "name": "CAUSE_EFFECT",
        "keywords": [
            "cause",
            "result",
            "effect",
            "reason",
            "purpose",
            "consequence",
            "lead to",
            "because",
            "therefore",
            "influence",
            "impact",
            "produce",
            "generate",
            "trigger",
        ],
        "tag": "A1.5+",
    },
    {
        "name": "GENERAL_ACTIONS",
        "keywords": [
            "do",
            "make",
            "act",
            "perform",
            "execute",
            "conduct",
            "carry out",
            "operate",
            "handle",
            "manage",
            "control",
            "start",
            "stop",
            "continue",
            "finish",
            "complete",
        ],
        "tag": "A2.1",
    },
    {
        "name": "PROPER_NAME",
        "keywords": [
            "name",
            "named",
            "called",
            "known as",
            "refers to",
            "abbreviation",
            "acronym",
            "title of",
            "brand",
        ],
        "tag": "Z3",
    },
    {
        "name": "PEOPLE_PERSON",
        "keywords": [
            "person",
            "people",
            "human",
            "man",
            "woman",
            "boy",
            "girl",
            "adult",
            "citizen",
            "individual",
            "someone",
            "somebody",
        ],
        "tag": "S2",
    },
    {
        "name": "POLITICS_GOVERNMENT",
        "keywords": [
            "politics",
            "political",
            "state",
            "nation",
            "country",
            "president",
            "minister",
            "election",
            "policy",
            "diplomatic",
            "parliament",
            "cabinet",
        ],
        "tag": "G1.1",
    },
    {
        "name": "LAW_ORDER",
        "keywords": [
            "law",
            "legal",
            "crime",
            "criminal",
            "police",
            "court",
            "judge",
            "trial",
            "prison",
            "arrest",
            "punish",
            "penalty",
        ],
        "tag": "G2.1",
    },
    {
        "name": "WAR_DEFENSE",
        "keywords": [
            "war",
            "battle",
            "military",
            "army",
            "soldier",
            "weapon",
            "defense",
            "attack",
            "combat",
            "troop",
        ],
        "tag": "G3",
    },
    {
        "name": "SCI_TECH",
        "keywords": [
            "science",
            "scientific",
            "technology",
            "technical",
            "computer",
            "software",
            "system",
            "machine",
            "device",
            "digital",
            "internet",
            "data",
        ],
        "tag": "Y1",
    },
    {
        "name": "TRAVEL_PLACE",
        "keywords": [
            "city",
            "town",
            "village",
            "capital",
            "country",
            "region",
            "province",
            "prefecture",
            "station",
            "airport",
            "port",
            "destination",
        ],
        "tag": "M7",
    },
    {
        "name": "BOOK_MEDIA",
        "keywords": [
            "book",
            "books",
            "novel",
            "dictionary",
            "newspaper",
            "magazine",
            "journal",
            "article",
            "paper",
            "document",
            "publication",
        ],
        "tag": "Q4.1",
    },
    {
        "name": "MUSIC_FILM_ARTS",
        "keywords": [
            "music",
            "musical",
            "song",
            "melody",
            "composer",
            "singer",
            "film",
            "movie",
            "cinema",
            "drama",
            "theater",
            "actor",
            "actress",
        ],
        "tag": "K2",
    },
    {
        "name": "SUBSTANCE_MATERIAL",
        "keywords": [
            "acid",
            "chemical",
            "substance",
            "material",
            "metal",
            "gas",
            "liquid",
            "solid",
            "water",
            "oil",
            "salt",
            "powder",
        ],
        "tag": "O1",
    },
    {
        "name": "LIFE_BIOLOGY",
        "keywords": [
            "life",
            "living thing",
            "species",
            "animal",
            "plant",
            "tree",
            "flower",
            "bird",
            "fish",
            "insect",
            "microbe",
            "bacteria",
        ],
        "tag": "L1",
    },
    {
        "name": "WORLD_GEO",
        "keywords": [
            "world",
            "earth",
            "japan",
            "chinese",
            "japanese",
            "country",
            "nation",
            "international",
            "global",
        ],
        "tag": "W1",
    },
]


def _norm_token(token: str) -> str:
    t = token.strip().lower()
    if not t:
        return ""
    for suf in ("ing", "ed", "es", "s"):
        if len(t) > len(suf) + 2 and t.endswith(suf):
            t = t[: -len(suf)]
            break
    return t


def _gloss_terms(gloss: str) -> set[str]:
    g = (gloss or "").strip().lower().replace("-", " ")
    parts = re.findall(r"[a-z0-9]+", g)
    terms = {_norm_token(p) for p in parts if p}
    return {t for t in terms if t}


def classify_to_usas(gloss: str, pos: str) -> str:
    g = (gloss or "").strip().lower()
    if not g:
        return "Z99"
    terms = _gloss_terms(g)
    # High-precision pre-checks for known competitive/movement semantics.
    if any(k in g for k in ("runner-up", "champion", "tournament", "semifinal", "finalist", "playoff", "league")):
        return "K5.2"
    if any(k in g for k in ("to run", "to walk", "to move", "to travel", "to go", "to come")):
        return "M1"
    best_tag = "Z99"
    best_score = 0
    for rule in RULES:
        score = 0
        for kw in rule["keywords"]:
            kw_norm = _norm_token(kw.replace("-", " ").strip().lower())
            if not kw_norm:
                continue
            if " " in kw_norm:
                if kw_norm in g:
                    score += 2
            else:
                if kw_norm in terms or kw_norm in g:
                    score += 1
        if score > best_score:
            best_score = score
            best_tag = str(rule["tag"])
    if best_score >= 1:
        return best_tag

    # POS fallback (only when no lexical rule matches)
    p = (pos or "").lower()
    grammar_meta = (
        "counter",
        "suffix",
        "prefix",
        "particle",
        "auxiliary",
        "kana",
        "kanji",
        "surname",
        "family name",
        "given name",
        "personal name",
        "place name",
        "abbreviation",
        "acronym",
    )
    if "verb" in p:
        return "A2.1"
    if "adjective" in p:
        return "A13"
    if "adverb" in p:
        return "A13"
    if "noun" in p:
        if not any(m in g for m in grammar_meta):
            return "A4.1"
    return "Z99"


def is_empty_or_punct_only(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return True
    return re.fullmatch(r"[\W_]+", s) is not None


def sanitize_jmdict_for_etree(xml_path: Path) -> Path:
    entity_pat = re.compile(r'<!ENTITY\s+([A-Za-z0-9_.-]+)\s+"([^"]*)">')
    ref_pat = re.compile(r"&([A-Za-z0-9_.-]+);")
    entities: dict[str, str] = {}
    in_doctype = False

    temp = tempfile.NamedTemporaryFile(prefix="jmdict_clean_", suffix=".xml", delete=False)
    tmp_path = Path(temp.name)
    with xml_path.open("r", encoding="utf-8", errors="replace") as src, tmp_path.open(
        "w", encoding="utf-8"
    ) as dst:
        for line in src:
            stripped = line.strip()
            if stripped.startswith("<!DOCTYPE"):
                in_doctype = True
                continue
            if in_doctype:
                m = entity_pat.search(line)
                if m:
                    entities[m.group(1)] = m.group(2)
                if "]>" in line:
                    in_doctype = False
                continue

            def repl(match: re.Match[str]) -> str:
                key = match.group(1)
                if key in entities:
                    return entities[key]
                # Keep standard XML entities untouched.
                if key in {"amp", "lt", "gt", "apos", "quot"}:
                    return f"&{key};"
                return ""

            dst.write(ref_pat.sub(repl, line))

    return tmp_path


def extract_entry(entry: ET.Element) -> tuple[list[str], list[str], str, str]:
    kebs = [e.text.strip() for e in entry.findall("./k_ele/keb") if e.text and e.text.strip()]
    rebs = [e.text.strip() for e in entry.findall("./r_ele/reb") if e.text and e.text.strip()]
    first_sense = entry.find("./sense")
    if first_sense is None:
        return kebs, rebs, "", ""

    pos_e = first_sense.find("./pos")
    pos = pos_e.text.strip() if (pos_e is not None and pos_e.text) else ""

    gloss = ""
    for g in first_sense.findall("./gloss"):
        lang = g.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        # In JMdict_e, many gloss nodes are English without explicit xml:lang.
        if (lang in (None, "", "eng")) and g.text and g.text.strip():
            gloss = g.text.strip()
            break
    return kebs, rebs, gloss, pos


def build_dict(xml_path: Path, output_path: Path) -> dict[str, str]:
    clean_xml = sanitize_jmdict_for_etree(xml_path)
    print(f"[info] Parsing sanitized XML: {clean_xml}")

    output_dict: dict[str, str] = {}
    total_entries = 0

    context = ET.iterparse(str(clean_xml), events=("end",))
    for _event, elem in context:
        if elem.tag != "entry":
            continue
        total_entries += 1
        if total_entries % 10000 == 0:
            print(f"[progress] entries processed: {total_entries}")

        kebs, rebs, gloss, pos = extract_entry(elem)
        if is_empty_or_punct_only(gloss):
            elem.clear()
            continue
        tag = classify_to_usas(gloss, pos)
        for key in kebs + rebs:
            if key and key not in output_dict:
                output_dict[key] = tag
        elem.clear()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Total entries processed: {total_entries}")
    print(f"Total keys in output dict: {len(output_dict)}")
    dist = Counter(output_dict.values())
    print("Tag distribution:")
    total_keys = max(1, len(output_dict))
    for tag, count in dist.most_common():
        print(f"{tag}: {count} ({count * 100.0 / total_keys:.1f}%)")

    test_cases = [
        ("準優勝", "K5.2"),
        ("優勝", "K5.2"),
        ("走る", "M1"),
        ("悲しい", "E4.1"),
        ("会社", "S5+"),
        ("山", "W3"),
        ("食べる", "F1"),
        ("考える", "X2.1"),
    ]
    print("Validation:")
    for lemma, expected in test_cases:
        result = output_dict.get(lemma, "NOT FOUND")
        status = "[OK]" if result == expected else "[NG]"
        print(f"{status} {lemma}: expected={expected}, got={result}")

    return output_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static JMdict -> USAS dictionary.")
    parser.add_argument(
        "--input",
        type=str,
        default="jmdict_builder/jmdict_e.xml",
        help="Path to JMdict XML (default: jmdict_builder/jmdict_e.xml)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="jmdict_builder/output/jmdict_usas.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    xml_path = Path(args.input)
    output_path = Path(args.output)
    if not xml_path.exists():
        print(f"JMdict XML not found: {xml_path}")
        print("Download command:")
        print('  python scripts/fetch_jmdict.py')
        print("or")
        print(
            '  powershell -NoProfile -Command "Invoke-WebRequest -Uri '
            "http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz -OutFile jmdict_builder/JMdict_e.gz; "
            "python -c \"import gzip,shutil; "
            "f_in=gzip.open('jmdict_builder/JMdict_e.gz','rb'); "
            "f_out=open('jmdict_builder/jmdict_e.xml','wb'); "
            "shutil.copyfileobj(f_in,f_out); f_in.close(); f_out.close()\""
            '"'
        )
        return 2

    build_dict(xml_path, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

