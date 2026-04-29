import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


WLSP_ENCODING = "cp932"
PAREN_RE = re.compile(r"[（(].*?[）)]")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def normalize_lemma(raw: str) -> str:
    text = PAREN_RE.sub("", raw).strip()
    text = text.replace("・", "").replace("‐", "-").replace("－", "-")
    return text


def parse_koumoku(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    with path.open("r", encoding=WLSP_ENCODING, errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split(",")
            if len(parts) >= 2:
                rows[parts[0].strip()] = parts[1].strip()
    return rows


def infer_usas_from_koumoku1_label(label: str) -> str | None:
    """
    High-confidence WLSP koumoku1 label -> USAS inference.
    Ordered from specific to general; rules for more specific domains
    (e.g. individual emotion types, crime, war) precede broader ones.

    WLSP labels use '・' (nakaguro) as a separator between related concepts.
    The patterns below match against the full label string.
    """
    text = (label or "").strip()
    if not text:
        return None

    rules: list[tuple[re.Pattern[str], str]] = [
        # ── G: Government, law, war ──────────────────────────────
        (re.compile(r"戦争|攻防|軍事|兵器|軍隊|兵営|軍人|防衛|武器|武装|弾薬"), "G3"),
        (re.compile(r"裁判|法律|捕縛|釈放|刑[^具]"), "G2.1"),
        (re.compile(r"犯罪|罪[^具]"), "G2.1"),
        (re.compile(r"倫理|道徳"), "G2.2"),
        (re.compile(r"政治|議会|政府|国家|国務|国際|行政|区画"), "G1.1"),
        (re.compile(r"公私"), "S1"),

        # ── E: Emotion (fine-grained) ───────────────────────────
        (re.compile(r"恐|[不心]安|怖"), "E5"),
        (re.compile(r"怒|暴力|暴行|いら|激高"), "E3"),
        (re.compile(r"快|喜|楽し|嬉|幸|満足|安[心神]"), "E4.1"),
        (re.compile(r"悲|苦悩|悲哀|嘆|哀|憂|愁|苦し"), "E4.2"),
        (re.compile(r"好悪|愛憎|好き|嫌い|好意|憎"), "E2"),
        (re.compile(r"心配|気遣い|懸念"), "E6"),
        (re.compile(r"恥|悔|反省|誇り|自信|自尊"), "E4"),

        # ── F: Food / Drink / Farming ───────────────────────────
        (re.compile(r"飲料|酒[^屋]|茶[^碗]|コーヒー|ソフトドリンク"), "F2"),
        (re.compile(r"煙草|たばこ|麻薬|覚醒|ドラッグ"), "F3"),
        (re.compile(r"農業|林業|園芸|牧畜|漁業|水産|農[^具]"), "F4"),
        (re.compile(r"菓子|スイーツ"), "F1"),
        (re.compile(r"料理|炊事|調理|米・|魚・|肉[^体]|調味"), "F1"),
        (re.compile(r"食[^堂]|食べ物|献立"), "F1"),

        # ── B: Body / Health ────────────────────────────────────
        (re.compile(r"病気|疾患|症状|[病患]気|体調|発病"), "B2"),
        (re.compile(r"障害|けが|怪我|負傷|外傷"), "B2"),
        (re.compile(r"医|治療|薬剤|薬品|診療|投薬"), "B3"),
        (re.compile(r"衛生|清潔|洗[面顔]|入浴|保健|公衆衛生"), "B4"),
        (re.compile(r"身体|頭|目|鼻|顔|胸|腹|手足|指|膜|筋|神経|内臓|皮|毛髪|羽毛|骨|歯|爪|角|体液|分泌|卵[^菓]"), "B1"),

        # ── K: Entertainment / Arts ─────────────────────────────
        (re.compile(r"演劇|舞台|劇場|ミュージカル"), "K4"),
        (re.compile(r"スポーツ|競技|運動|球技|陸上"), "K5.1"),
        (re.compile(r"ゲーム|遊戯|玩具|おもちゃ"), "K5.2"),
        (re.compile(r"子[供ども].*遊|遊.*子[供ども]"), "K6"),
        (re.compile(r"いたずら|騒ぎ"), "K6"),
        (re.compile(r"音楽|楽器|演奏|歌|作曲|レコード|録音"), "K2"),
        (re.compile(r"芸術|美術|絵|彫刻|工芸|文芸"), "C1"),

        # ── M: Movement / Transport ─────────────────────────────
        (re.compile(r"飛行|航空|空港|空中|滑走路|宇宙[^人]"), "M5"),
        (re.compile(r"船舶|航海|船[^主]|港|海上|海運|舟"), "M4"),
        (re.compile(r"運輸|交通|乗り物|車[^い]|鉄道|道路|駅"), "M3"),
        (re.compile(r"移動|発着|走り|飛び|流れ|巡回|通過|往復|出入"), "M1"),
        (re.compile(r"持ち|運び|取り|置き|配送|引越"), "M2"),

        # ── O: Objects / Physical ───────────────────────────────
        (re.compile(r"電気|電子|電源|電力|電池|配線"), "O3"),
        (re.compile(r"色[^々]|色彩|カラー|模様"), "O4.3"),
        (re.compile(r"美醜|美し|[^不]美人|醜"), "O4.2"),
        (re.compile(r"温度|[寒暑]暖|熱[^心]|冷た"), "O4.6"),
        (re.compile(r"形・|型・|姿・|構え|角など|玉・|凹凸|穴・|束・|片・"), "O4.4"),

        # ── Q: Communication / Media ────────────────────────────
        (re.compile(r"放送|ラジオ|テレビ|TV|映画|ビデオ"), "Q4.3"),
        (re.compile(r"新聞|雑誌|ニュース|[報道]"), "Q4.2"),
        (re.compile(r"書籍|本屋|書物|文庫|出版|図書|文献"), "Q4.1"),
        (re.compile(r"通信|電信|電話|伝達|報知|合図"), "Q1.3"),
        (re.compile(r"書き|読み|文章|文書|目録|暦|翻訳"), "Q1.2"),
        (re.compile(r"挨拶|話・|談話|問答|会議|論議|言論"), "Q2.1"),

        # ── S: Social ───────────────────────────────────────────
        (re.compile(r"男性|女性|男女|男[^女]|女[^男]|性別"), "S2"),
        (re.compile(r"親族|親戚|家族|夫婦|親・|先祖|子・|子孫|兄弟"), "S4"),
        (re.compile(r"宗教|信仰|神仏|神・|教会|寺|仏|精霊|霊"), "S9"),
        (re.compile(r"義務|必要[^条]|不可欠"), "S6"),
        (re.compile(r"援助|助け|救護|救援|救援|支援|協力|参加|奉仕"), "S8"),
        (re.compile(r"妨害|邪魔|阻止|阻害|障害|干渉|侵害"), "S8"),
        (re.compile(r"競争|競い|勝負|戦い|試合"), "S7.3"),
        (re.compile(r"許可|許容|認可|免許|承認"), "S7.4"),
        (re.compile(r"賞罰|罰[^金]|褒美|表彰|叱"), "S7.2"),
        (re.compile(r"人柄|人格|性格|個性"), "S1.2"),
        (re.compile(r"脅迫|中傷|愚弄|侮辱|罵"), "S1.2.5"),

        # ── H: Housing / Buildings ──────────────────────────────
        (re.compile(r"家具|調度|机|椅子|ベッド|棚"), "H5"),
        (re.compile(r"家屋|建物|建築|門・|塀"), "H1"),
        (re.compile(r"部屋|床・|廊下|階段|屋根|柱|壁|窓|天井|戸・|カーテン|敷物"), "H2"),
        (re.compile(r"住[^み]|居住|住宅|住居|寝[^具]|宿[^泊]"), "H4"),

        # ── M7 / W3: Places ──────────────────────────────────────
        (re.compile(r"郷里|故郷|都会|田舎|町[^内]|村[^内]|市[^場]"), "M7"),
        (re.compile(r"地名|地相|地帯|景[^色]|山野|川・|湖[^南]|海・|島[^国]|岸"), "W3"),
        (re.compile(r"土地利用|地類"), "W3"),

        # ── T: Time ─────────────────────────────────────────────
        (re.compile(r"新旧|遅速|古[^代]・|新し|若[^者]|老[^人]|年配|年齢"), "T3"),
        (re.compile(r"開始|始ま|終了|終わ|中止|停止|J?始"), "T2"),
        (re.compile(r"早[^速]|遅[^速]"), "T4"),
        (re.compile(r"時間|時刻|期間|年[^配]|月[^日]|日[^常]|週・|朝晩|現在|過去|未来|季節|時代|順序|場合"), "T1"),

        # ── X: Psychological / Mental ───────────────────────────
        (re.compile(r"調査|検査|探索|探し|研究|試験|テスト"), "X2.4"),
        (re.compile(r"理解|把握|わかる|把握|頷"), "X2.5"),
        (re.compile(r"期待|予想|予期|予測|見込"), "X2.6"),
        (re.compile(r"選[^手]|選択|取捨|選抜"), "X7"),
        (re.compile(r"試み|試行|挑戦|挑み|企て"), "X8"),
        (re.compile(r"成功|失敗|成績|結果[^的]|勝敗"), "X9.2"),
        (re.compile(r"注意|注目|関心[^無]|興味[^無]"), "X5.1"),
        (re.compile(r"興奮|退屈|刺激|活気|熱意"), "X5.2"),
        (re.compile(r"計算|算数|数学|数式|幾何|統計"), "N2"),
        (re.compile(r"測定|計測|計量|長短|高低|深浅|厚薄|遠近|広狭|大小|軽重|速度|角度|量[^的]"), "N3"),
        (re.compile(r"頻度|回数|何度|度合い|度数|毎"), "N6"),

        # ── Sensory ──────────────────────────────────────────────
        (re.compile(r"味[^見]|風味|食味|旨み"), "X3.1"),
        (re.compile(r"音[^楽]|音韻|声[^援]|響き|騒音|うるさ"), "X3.2"),
        (re.compile(r"触[^れ]|手触り|肌触り"), "X3.3"),
        (re.compile(r"見[^るせせ]|視覚|眺め|見[^聞]"), "X3.4"),
        (re.compile(r"匂い|臭[^い]|臭覚|におい|香[^港]|匂"), "X3.5"),

        # ── Other specific domains ──────────────────────────────
        (re.compile(r"情報技術|コンピュータ|IT|ソフトウェア|ネットワーク"), "Y2"),
        (re.compile(r"環境|自然保護|公害|リサイクル|省エネ"), "W5"),
        (re.compile(r"天気|気象|風[^呂]|雲[^散]|雨・|雪[^国]|晴|嵐"), "W4"),
        (re.compile(r"光[^景]|明る|照明|灯"), "W2"),
        (re.compile(r"宇宙|天体|天象|星・|惑星|太陽|月[^見日]"), "W1"),
        (re.compile(r"お金|金銭|貨幣|収支|経済|財[^政]|金[^属]|資[^産]本|価格|費用|給与|料金|利子|損得|税[^金]|貸借|貧富"), "I1"),
        (re.compile(r"商売|商業|取引|売買|実業"), "I2"),
        (re.compile(r"仕事|職業|労働|勤め|作業|雇用|採用|休暇|退職"), "I3"),

        # ── Broader fallbacks (ordered last to avoid over-capture) ──
        (re.compile(r"教育|学習|学校|学[^生]|教[^会]|学問|学科|訓練|養成|練習"), "P1"),
        (re.compile(r"言語|語[^学]|文法|文字|表現|叙述|名[^前]"), "Q1"),
        (re.compile(r"衣|服|被服|履[^歴]|装い|着物"), "B5"),
        (re.compile(r"植物|樹|草|花[^火]|葉[^書]|茎|根[^本]|果[^実]"), "L3"),
        (re.compile(r"動物|哺乳|鳥[^瞰]|爬虫|両生|魚[^介]|昆虫|獣"), "L2"),
        (re.compile(r"人間|人[^生]|われ|なれ|人種|民族|国民|住民|君主|人物"), "S2"),

        # ── Most generic / previously existing ──────────────────
        (re.compile(r"空間|場所|方向|方角"), "M6"),
        (re.compile(r"一般|抽象|事柄|[こそ]の"), "A1"),
    ]
    for pattern, code in rules:
        if pattern.search(text):
            return code
    return None


def parse_koumoku_codes(path: Path) -> list[str]:
    codes: list[str] = []
    with path.open("r", encoding=WLSP_ENCODING, errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split(",")
            if parts and parts[0].strip():
                codes.append(parts[0].strip())
    return codes


def parse_wlsp_entries(path: Path) -> list[dict]:
    entries: list[dict] = []
    with path.open("r", encoding=WLSP_ENCODING, errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split(",")
            if len(parts) < 15:
                continue
            class_code = parts[7].strip()
            top_code = class_code[:4]
            surface = parts[11].strip()
            lemma = normalize_lemma(parts[12].strip())
            reading = parts[13].strip()
            if not lemma:
                continue
            entries.append(
                {
                    "class_code": class_code,
                    "top_code": top_code,
                    "surface": surface,
                    "lemma": lemma,
                    "reading": reading,
                }
            )
    return entries


def resolve_usas_code(entry: dict, fine_map: dict[str, str], top_map: dict[str, str]) -> tuple[str | None, str]:
    class_code = entry["class_code"]
    top_code = entry["top_code"]
    fine_hit = resolve_with_prefix_map(class_code, fine_map)
    if fine_hit is not None:
        return fine_hit, "koumoku1"
    top_hit = resolve_with_prefix_map(top_code, top_map)
    if top_hit is not None:
        return top_hit, "top"
    return None, "unmapped"


def wlsp_code_candidates(code: str) -> list[str]:
    """
    Build key candidates from most specific to most general.
    Example: 1.1527 -> [1.1527, 1.152, 1.15, 1.1]
    """
    if "." not in code:
        return [code]
    head, tail = code.split(".", 1)
    candidates = [code]
    for n in range(len(tail) - 1, 0, -1):
        candidates.append(f"{head}.{tail[:n]}")
    return candidates


def resolve_with_prefix_map(code: str, mapping: dict[str, str]) -> str | None:
    for candidate in wlsp_code_candidates(code):
        if candidate in mapping:
            return mapping[candidate]
    return None


def rebuild_fine_mapping(
    koumoku1_codes: list[str],
    fine_map: dict[str, str],
    top_map: dict[str, str],
) -> dict[str, str]:
    """
    Rebuild a full koumoku1 -> USAS map.
    Priority:
      1) explicit/prefix fine map
      2) top-level fallback
    """
    rebuilt: dict[str, str] = {}
    for code in sorted(set(koumoku1_codes)):
        usas = resolve_with_prefix_map(code, fine_map)
        if usas is None:
            usas = resolve_with_prefix_map(code[:4], top_map)
        if usas is not None:
            rebuilt[code] = usas
    return rebuilt


def rebuild_fine_mapping_from_labels(
    fine_labels: dict[str, str],
    fine_map: dict[str, str],
    top_map: dict[str, str],
) -> tuple[dict[str, str], dict[str, int]]:
    """
    Rebuild full koumoku1 mapping with this priority:
      1) high-confidence label inference
      2) explicit/prefix fine_map
      3) top-level fallback
    """
    rebuilt: dict[str, str] = {}
    source_counter: Counter = Counter()
    for code in sorted(fine_labels):
        inferred = infer_usas_from_koumoku1_label(fine_labels.get(code, ""))
        if inferred is not None:
            rebuilt[code] = inferred
            source_counter["label_inference"] += 1
            continue
        usas = resolve_with_prefix_map(code, fine_map)
        if usas is not None:
            rebuilt[code] = usas
            source_counter["fine_map"] += 1
            continue
        usas = resolve_with_prefix_map(code[:4], top_map)
        if usas is not None:
            rebuilt[code] = usas
            source_counter["top_map"] += 1
    return rebuilt, dict(source_counter)


def validate_usas_codes(mapping: dict[str, str], usas_categories: dict[str, dict]) -> list[str]:
    invalid: list[str] = []
    for key, usas in mapping.items():
        if usas not in usas_categories:
            invalid.append(f"{key} -> {usas}")
    return sorted(invalid)


def build_lexicon(entries: list[dict], fine_map: dict[str, str], top_map: dict[str, str]) -> tuple[dict[str, list[str]], dict]:
    lexicon: dict[str, set[str]] = defaultdict(set)
    mapped_counter: Counter = Counter()
    unmapped_counter: Counter = Counter()
    top_samples: dict[str, list[str]] = defaultdict(list)
    mapping_level_counter: Counter = Counter()

    for entry in entries:
        top_code = entry["top_code"]
        lemma = entry["lemma"]
        usas_code, level = resolve_usas_code(entry, fine_map, top_map)
        if usas_code is None:
            unmapped_counter[top_code] += 1
            if len(top_samples[top_code]) < 10 and lemma not in top_samples[top_code]:
                top_samples[top_code].append(lemma)
            continue
        lexicon[usas_code].add(lemma)
        mapped_counter[usas_code] += 1
        mapping_level_counter[level] += 1

    sorted_lexicon = {
        usas_code: sorted(lemmas)
        for usas_code, lemmas in sorted(lexicon.items(), key=lambda item: item[0])
    }
    report = {
        "entry_count": len(entries),
        "mapped_entry_count": sum(mapped_counter.values()),
        "mapped_domain_count": len(sorted_lexicon),
        "mapping_levels": dict(mapping_level_counter),
        "unmapped_top_codes": [
            {
                "wlsp_top_code": code,
                "count": count,
                "samples": top_samples.get(code, []),
            }
            for code, count in unmapped_counter.most_common()
        ],
        "usas_distribution": dict(mapped_counter.most_common()),
    }
    return sorted_lexicon, report


def build_catalog(entries: list[dict], fine_map: dict[str, str], top_map: dict[str, str], top_labels: dict[str, str], fine_labels: dict[str, str]) -> dict:
    catalog_rows = []
    for entry in entries:
        usas_code, mapping_level = resolve_usas_code(entry, fine_map, top_map)
        catalog_rows.append(
            {
                "lemma": entry["lemma"],
                "surface": entry["surface"],
                "reading": entry["reading"],
                "wlsp_code": entry["class_code"],
                "wlsp_top_code": entry["top_code"],
                "wlsp_top_label": top_labels.get(entry["top_code"], ""),
                "wlsp_fine_label": fine_labels.get(entry["class_code"], ""),
                "usas_code": usas_code or "Z99",
                "mapping_level": mapping_level,
            }
        )
    return {"entries": catalog_rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a USAS lexicon from local WLSP data.")
    parser.add_argument(
        "--wlsp-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "WLSP-master",
        help="Directory containing WLSP-master source files.",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "wlsp_to_usas_map.json",
        help="Path to WLSP top-level -> USAS mapping JSON.",
    )
    parser.add_argument(
        "--fine-mapping",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "wlsp_koumoku1_to_usas_map.json",
        help="Path to WLSP koumoku1 -> USAS mapping JSON.",
    )
    parser.add_argument(
        "--output-lexicon",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "lexicon_wlsp_usas.json",
        help="Output JSON lexicon path.",
    )
    parser.add_argument(
        "--output-report",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "wlsp_mapping_report.json",
        help="Output mapping report path.",
    )
    parser.add_argument(
        "--output-catalog",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "wlsp_usas_catalog.json",
        help="Output row-level catalog path.",
    )
    parser.add_argument(
        "--usas-categories",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "usas_categories.json",
        help="USAS categories JSON path for validation.",
    )
    parser.add_argument(
        "--refresh-fine-mapping",
        action="store_true",
        help="Rebuild full koumoku1 mapping before lexicon build.",
    )
    parser.add_argument(
        "--write-refreshed-fine-to",
        type=Path,
        default=None,
        help="Write refreshed fine mapping JSON to this path.",
    )
    parser.add_argument(
        "--rebuild-fine-from-labels",
        action="store_true",
        help="Rebuild full koumoku1 mapping using label-based inference first.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wlsp_dir = args.wlsp_dir
    top_mapping_payload = load_json(args.mapping)
    fine_mapping_payload = load_json(args.fine_mapping)
    top_map = {key: value for key, value in top_mapping_payload.items() if not key.startswith("_")}
    fine_map = {key: value for key, value in fine_mapping_payload.items() if not key.startswith("_")}
    usas_categories = load_json(args.usas_categories)

    top_labels = parse_koumoku(wlsp_dir / "koumoku2.txt")
    fine_labels = parse_koumoku(wlsp_dir / "koumoku1.txt")
    fine_codes = parse_koumoku_codes(wlsp_dir / "koumoku1.txt")
    rebuild_sources: dict[str, int] | None = None

    if args.rebuild_fine_from_labels:
        fine_map, rebuild_sources = rebuild_fine_mapping_from_labels(
            fine_labels=fine_labels,
            fine_map=fine_map,
            top_map=top_map,
        )
    elif args.refresh_fine_mapping:
        fine_map = rebuild_fine_mapping(fine_codes, fine_map, top_map)
        if args.write_refreshed_fine_to:
            dump_json(
                args.write_refreshed_fine_to,
                {
                    "_meta": {
                        "source": "WLSP koumoku1 fine-grained semantic classes",
                        "strategy": "Rebuilt full mapping from explicit/prefix fine mappings plus top-level fallback.",
                        "generated_by": "scripts/build_wlsp_lexicon.py",
                    },
                    **fine_map,
                },
            )
    if args.write_refreshed_fine_to and args.rebuild_fine_from_labels:
        dump_json(
            args.write_refreshed_fine_to,
            {
                "_meta": {
                    "source": "WLSP koumoku1 fine-grained semantic classes",
                    "strategy": "Rebuilt full mapping using label inference first, then fine-map prefix, then top fallback.",
                    "generated_by": "scripts/build_wlsp_lexicon.py --rebuild-fine-from-labels",
                },
                **fine_map,
            },
        )

    entries = parse_wlsp_entries(wlsp_dir / "bunruidb.txt")

    lexicon, report = build_lexicon(entries, fine_map, top_map)
    catalog = build_catalog(entries, fine_map, top_map, top_labels, fine_labels)
    report["wlsp_top_labels"] = {code: top_labels.get(code, "") for code in sorted(top_labels)}
    report["top_mapping_source"] = str(args.mapping)
    report["fine_mapping_source"] = str(args.fine_mapping)
    report["source_wlsp_dir"] = str(wlsp_dir)
    report["invalid_top_mappings"] = validate_usas_codes(top_map, usas_categories)
    report["invalid_fine_mappings"] = validate_usas_codes(fine_map, usas_categories)
    report["fine_mapping_size"] = len(fine_map)
    report["refreshed_fine_mapping"] = bool(args.refresh_fine_mapping)
    report["rebuild_fine_from_labels"] = bool(args.rebuild_fine_from_labels)
    if rebuild_sources is not None:
        report["rebuild_sources"] = rebuild_sources

    dump_json(args.output_lexicon, lexicon)
    dump_json(args.output_report, report)
    dump_json(args.output_catalog, catalog)

    print(json.dumps(
        {
            "output_lexicon": str(args.output_lexicon),
            "output_report": str(args.output_report),
            "output_catalog": str(args.output_catalog),
            "mapped_domains": len(lexicon),
            "mapped_entries": report["mapped_entry_count"],
            "total_entries": report["entry_count"],
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
