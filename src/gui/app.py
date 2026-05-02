from __future__ import annotations

import csv
import json
import tkinter as tk
from collections import Counter, defaultdict
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from src.analysis.compare import build_comparison
from src.analysis.context import (
    build_context_detail,
)
from src.gui.analysis_controller import (
    build_domain_word_table_rows,
    build_profile_rows,
    build_profile_summary_lines,
    parse_numeric_options,
    run_analysis,
)
from src.i18n import SUPPORTED_LANGUAGES, tr
from src.services.analysis_service import kwic_from_result
from src.project import open_project_file, save_project_file
from src.utils.file_io import (
    push_recent_file,
    read_json_file,
    read_recent_files,
    read_text_file,
    write_csv,
    write_csv_bundle,
    write_json,
    write_recent_files,
)


EXTRA_TEXTS = {
    "subtitle": {
        "zh": "日语语义域研究工作台",
        "ja": "日本語セマンティック研究ワークベンチ",
        "en": "Japanese semantic research workbench",
    },
    "workspace": {"zh": "工作台", "ja": "ワークベンチ", "en": "Workbench"},
    "profile": {"zh": "语义域", "ja": "意味領域", "en": "Semantic Profile"},
    "kwic": {"zh": "共现", "ja": "共起", "en": "KWIC"},
    "lexicon_center": {"zh": "词典中心", "ja": "辞書センター", "en": "Lexicon Center"},
    "compare_center": {"zh": "对比", "ja": "比較", "en": "Compare"},
    "help_center": {"zh": "帮助", "ja": "ヘルプ", "en": "Help"},
    "open": {"zh": "打开", "ja": "開く", "en": "Open"},
    "save_project_short": {"zh": "保存项目", "ja": "保存", "en": "Save Project"},
    "semantic_tagger": {"zh": "语义域标记", "ja": "意味領域タグ付け", "en": "Semantic Tagger"},
    "export": {"zh": "导出", "ja": "出力", "en": "Export"},
    "domain_summary": {"zh": "域摘要", "ja": "領域サマリー", "en": "Domain Summary"},
    "domain_words": {"zh": "域下词汇", "ja": "領域語彙", "en": "Domain Words"},
    "official_desc": {"zh": "官方定义", "ja": "公式定義", "en": "Official Description"},
    "relative_10k": {"zh": "每万词频", "ja": "1万語あたり", "en": "Per 10k"},
    "types_tokens": {"zh": "类型 / 词元", "ja": "タイプ / トークン", "en": "Types / Tokens"},
    "line": {"zh": "行", "ja": "行", "en": "Line"},
    "left_context": {"zh": "左上下文", "ja": "左文脈", "en": "Left Context"},
    "right_context": {"zh": "右上下文", "ja": "右文脈", "en": "Right Context"},
    "current_target": {"zh": "当前目标", "ja": "現在ターゲット", "en": "Current Target"},
    "detail_popup": {"zh": "原文定位", "ja": "原文定位", "en": "Context Detail"},
    "source_offset": {"zh": "原文偏移", "ja": "オフセット", "en": "Source Offset"},
    "confidence": {"zh": "置信度", "ja": "信頼度", "en": "Confidence"},
    "domain_filter": {"zh": "域过滤", "ja": "領域フィルタ", "en": "Domain Filter"},
    "refresh": {"zh": "刷新", "ja": "更新", "en": "Refresh"},
    "copy_row": {"zh": "复制本行", "ja": "行をコピー", "en": "Copy Row"},
    "jump_source": {"zh": "跳到原文", "ja": "原文へ移動", "en": "Jump to Source"},
    "view_kwic": {"zh": "查看共现", "ja": "共起を見る", "en": "View KWIC"},
    "view_domain_words": {"zh": "查看域词汇", "ja": "領域語彙を見る", "en": "View Domain Words"},
    "move_to_domain": {"zh": "移动到其他域", "ja": "他の領域へ移動", "en": "Move to Another Domain"},
    "add_to_current_domain": {"zh": "加入当前域", "ja": "現在領域へ追加", "en": "Add to Current Domain"},
    "view_in_lexicon": {"zh": "在词典中查看", "ja": "辞書で表示", "en": "View in Lexicon"},
    "lexicon_domains": {"zh": "词典域", "ja": "辞書領域", "en": "Domains"},
    "lexicon_terms": {"zh": "词条", "ja": "語彙", "en": "Terms"},
    "batch_import": {"zh": "批量导入", "ja": "一括取込", "en": "Batch Import"},
    "import_text": {"zh": "粘贴导入", "ja": "貼り付け取込", "en": "Paste Import"},
    "import_file": {"zh": "文件导入", "ja": "ファイル取込", "en": "Import File"},
    "remove_term": {"zh": "删除词条", "ja": "語彙削除", "en": "Remove Term"},
    "remove_domain": {"zh": "删除域", "ja": "領域削除", "en": "Remove Domain"},
    "lexicon_saved": {"zh": "词典已保存", "ja": "辞書を保存しました", "en": "Lexicon saved"},
    "target_domain": {"zh": "目标域", "ja": "ターゲット領域", "en": "Target Domain"},
    "set_selected_domain": {"zh": "设置选中词域", "ja": "選択語へ領域設定", "en": "Set Selected Domain"},
    "import_selected_lemma": {"zh": "导入选中原型", "ja": "選択原形を導入", "en": "Import Selected Lemmas"},
    "import_all_lemma": {"zh": "导入全部原型", "ja": "全原形を導入", "en": "Import All Lemmas"},
    "lemma_note": {"zh": "写入词典时始终使用 lemma。", "ja": "辞書への保存は常に lemma を使います。", "en": "Lexicon import always uses lemma."},
    "menu_file": {"zh": "文件", "ja": "ファイル", "en": "File"},
    "menu_view": {"zh": "视图", "ja": "表示", "en": "View"},
    "menu_tools": {"zh": "工具", "ja": "ツール", "en": "Tools"},
    "menu_help": {"zh": "帮助", "ja": "ヘルプ", "en": "Help"},
    "about": {"zh": "关于", "ja": "このソフトについて", "en": "About"},
    "help_text": {
        "zh": "主链路：语义域频次 -> 域下词汇 -> KWIC -> 原文定位。\n\n本软件聚焦日语语义域研究的核心模块：文本分析、语义域剖面、KWIC、词典维护、双文本对比与帮助。\n\n词典导入与改标会优先写入 lemma，而不是表层词形。",
        "ja": "主な流れ：意味領域頻度 -> 領域語彙 -> KWIC -> 原文詳細。\n\n本ソフトは日本語の意味領域分析に必要な機能（テキスト分析、プロファイル、KWIC、辞書、比較、ヘルプ）に集中しています。",
        "en": "Core flow: semantic profile -> domain words -> KWIC -> context detail.\n\nThis app focuses on the core modules for Japanese semantic domain analysis: analysis, profile, KWIC, lexicon, compare, and help.",
    },
    "about_text": {
        "zh": "许可协议: CC-BY-NC-ND 4.0\n作者组织: 新疆大学外国语学院\n作者: 张闻泽\n许可图标: image/by-nc-nd.svg",
        "ja": "ライセンス: CC-BY-NC-ND 4.0\n所属: 新疆大学外国语学院\n作者: 张闻泽\nライセンスアイコン: image/by-nc-nd.svg",
        "en": "License: CC-BY-NC-ND 4.0\nOrganization: School of Foreign Languages, Xinjiang University\nAuthor: Zhang Wenze\nLicense icon: image/by-nc-nd.svg",
    },
    "switch_done": {"zh": "已切换视图", "ja": "表示を切り替えました", "en": "View switched"},
    "kwic_need_keyword": {
        "zh": "请输入检索关键词后再刷新 KWIC。",
        "ja": "KWIC を更新するにはキーワードを入力してください。",
        "en": "Enter a keyword before refreshing KWIC.",
    },
    "compare_need_both": {
        "zh": "请在左右两侧都输入文本后再运行对比。",
        "ja": "左右のテキストを入力してから比較を実行してください。",
        "en": "Enter text in both columns before running compare.",
    },
    "kwic_export_empty": {
        "zh": "没有可导出的 KWIC 行。请先分析并刷新 KWIC。",
        "ja": "出力できる KWIC 行がありません。分析後に更新してください。",
        "en": "No KWIC rows to export. Run analysis and refresh KWIC first.",
    },
    "kwic_export_saved": {
        "zh": "KWIC 已导出",
        "ja": "KWIC を出力しました",
        "en": "KWIC exported",
    },
    "lexicon_need_domain": {
        "zh": "请选择或填写语义域代码。",
        "ja": "意味領域コードを選択または入力してください。",
        "en": "Select or enter a domain code.",
    },
    "lexicon_need_terms": {
        "zh": "请至少输入一行词条。",
        "ja": "語彙を1行以上入力してください。",
        "en": "Enter at least one lemma line.",
    },
}


class WmatrixJAApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.base_dir = Path(__file__).resolve().parents[2]
        self.default_lexicon = self.base_dir / "data" / "lexicon.json"
        self.categories_path = self.base_dir / "data" / "usas_categories.json"
        self.recent_path = self.base_dir / "data" / "recent_files.json"

        self.language_var = tk.StringVar(value="zh")
        self.mode_var = tk.StringVar(value="C")
        self.lexicon_var = tk.StringVar(value=str(self.default_lexicon))
        self.min_freq_var = tk.StringVar(value="1")
        self.top_n_var = tk.StringVar(value="")
        self.unknown_domain_var = tk.StringVar(value="Z99")
        self.keyword_var = tk.StringVar(value="")
        self.selected_domain_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")
        self.current_view_var = tk.StringVar(value="workspace")

        self.last_result: dict | None = None
        self.left_result: dict | None = None
        self.right_result: dict | None = None
        self.current_project_path: Path | None = None
        self.recent_files = read_recent_files(self.recent_path)
        self.categories = read_json_file(str(self.categories_path))

        self.nav_buttons: dict[str, ttk.Button] = {}
        self.view_frames: dict[str, ttk.Frame] = {}
        self.profile_domain_map: dict[str, dict] = {}
        self.kwic_rows: list[dict] = []
        self._busy_depth = 0

        self._configure_style()
        self._build_layout()
        self._build_menubar()
        self._apply_language()
        self._load_sample_if_present()
        self._refresh_status_ready()

    @property
    def current_language(self) -> str:
        return self.language_var.get().strip() or "en"

    def _t(self, key: str) -> str:
        translated = tr(self.current_language, key)
        if translated != key:
            return translated
        return EXTRA_TEXTS.get(key, {}).get(self.current_language, EXTRA_TEXTS.get(key, {}).get("en", key))

    def _configure_style(self) -> None:
        self.root.configure(bg="#edf1f7")
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=("Segoe UI", 10))
        style.configure("App.TFrame", background="#edf1f7")
        style.configure("Surface.TFrame", background="#ffffff")
        style.configure("Sidebar.TFrame", background="#162032")
        style.configure("SidebarTitle.TLabel", background="#162032", foreground="#f5f7fb", font=("Segoe UI Semibold", 16))
        style.configure("SidebarSub.TLabel", background="#162032", foreground="#9ab0d0")
        style.configure("Sidebar.TButton", background="#162032", foreground="#f5f7fb", padding=(14, 10), relief="flat")
        style.map("Sidebar.TButton", background=[("active", "#253453"), ("pressed", "#253453")])
        style.configure("Primary.TButton", padding=(12, 8), background="#1368ce", foreground="#ffffff")
        style.map("Primary.TButton", background=[("active", "#0e58af")])
        style.configure("Ghost.TButton", padding=(10, 7), background="#f3f6fb")
        style.configure("Card.TLabelframe", background="#ffffff", borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", background="#ffffff", foreground="#24324b", font=("Segoe UI Semibold", 11))
        style.configure("Header.TLabel", background="#edf1f7", foreground="#16233b", font=("Segoe UI Semibold", 18))
        style.configure("Subtle.TLabel", background="#edf1f7", foreground="#5b6980")
        style.configure("StatTitle.TLabel", background="#ffffff", foreground="#7b8799", font=("Segoe UI", 9))
        style.configure("StatValue.TLabel", background="#ffffff", foreground="#18263d", font=("Segoe UI Semibold", 15))
        style.configure("Treeview", rowheight=28, fieldbackground="#ffffff", background="#ffffff", bordercolor="#d9e0ea")
        style.configure("Treeview.Heading", background="#eef2f8", foreground="#24324b", font=("Segoe UI Semibold", 10))
        style.map("Treeview", background=[("selected", "#dbe7ff")], foreground=[("selected", "#111827")])
        style.configure("Kwic.Treeview", font=("Consolas", 10), rowheight=28)
        style.configure("Kwic.Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _build_layout(self) -> None:
        self.root.title("Bunseki")
        self.root.geometry("1520x940")
        self.root.minsize(1240, 760)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", padding=(16, 20))
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.columnconfigure(0, weight=1)

        ttk.Label(self.sidebar, text="Bunseki", style="SidebarTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.sidebar_subtitle = ttk.Label(self.sidebar, style="SidebarSub.TLabel")
        self.sidebar_subtitle.grid(row=1, column=0, sticky="w", pady=(6, 18))

        nav_items = [
            ("workspace", "workspace"),
            ("profile", "profile"),
            ("kwic", "kwic"),
            ("lexicon", "lexicon_center"),
            ("compare", "compare_center"),
            ("help", "help_center"),
        ]
        for row_index, (view_key, label_key) in enumerate(nav_items, start=2):
            button = ttk.Button(
                self.sidebar,
                style="Sidebar.TButton",
                command=lambda key=view_key: self._switch_view(key),
            )
            button.grid(row=row_index, column=0, sticky="ew", pady=3)
            self.nav_buttons[view_key] = button
            setattr(self, f"{view_key}_nav_label_key", label_key)

        self.main = ttk.Frame(self.root, style="App.TFrame", padding=(18, 16, 18, 18))
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(2, weight=1)

        self.header = ttk.Frame(self.main, style="App.TFrame")
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(0, weight=1)
        ttk.Label(self.header, text="Bunseki", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.header_subtitle = ttk.Label(self.header, style="Subtle.TLabel")
        self.header_subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.toolbar = ttk.LabelFrame(self.main, style="Card.TLabelframe", padding=(12, 10))
        self.toolbar.grid(row=1, column=0, sticky="ew", pady=(14, 14))
        for index in range(16):
            self.toolbar.columnconfigure(index, weight=0)
        self.toolbar.columnconfigure(15, weight=1)

        self.open_button = ttk.Button(self.toolbar, style="Ghost.TButton", command=self._open_text_file)
        self.open_button.grid(row=0, column=0, padx=(0, 8))
        self.analyze_button = ttk.Button(self.toolbar, style="Primary.TButton", command=self._analyze_primary)
        self.analyze_button.grid(row=0, column=1, padx=(0, 8))
        self.save_project_button = ttk.Button(self.toolbar, style="Ghost.TButton", command=self._save_project)
        self.save_project_button.grid(row=0, column=2, padx=(0, 8))
        self.export_button = ttk.Button(self.toolbar, style="Ghost.TButton", command=self._export_json)
        self.export_button.grid(row=0, column=3, padx=(0, 16))

        self.lexicon_label = ttk.Label(self.toolbar)
        self.lexicon_label.grid(row=0, column=4, sticky="w", padx=(0, 8))
        ttk.Entry(self.toolbar, textvariable=self.lexicon_var, width=34).grid(row=0, column=5, padx=(0, 6))
        self.browse_button = ttk.Button(self.toolbar, command=self._choose_lexicon)
        self.browse_button.grid(row=0, column=6, padx=(0, 14))

        self.language_label = ttk.Label(self.toolbar)
        self.language_label.grid(row=0, column=7, sticky="w", padx=(0, 8))
        self.language_box = ttk.Combobox(self.toolbar, textvariable=self.language_var, state="readonly", values=list(SUPPORTED_LANGUAGES), width=6)
        self.language_box.grid(row=0, column=8, padx=(0, 12))
        self.language_box.bind("<<ComboboxSelected>>", lambda _event: self._on_language_changed())

        self.mode_label = ttk.Label(self.toolbar)
        self.mode_label.grid(row=0, column=9, sticky="w", padx=(0, 8))
        ttk.Combobox(self.toolbar, textvariable=self.mode_var, state="readonly", values=["A", "B", "C"], width=4).grid(row=0, column=10, padx=(0, 12))

        self.min_freq_label = ttk.Label(self.toolbar)
        self.min_freq_label.grid(row=0, column=11, sticky="w", padx=(0, 8))
        ttk.Entry(self.toolbar, textvariable=self.min_freq_var, width=6).grid(row=0, column=12, padx=(0, 12))

        self.top_n_label = ttk.Label(self.toolbar)
        self.top_n_label.grid(row=0, column=13, sticky="w", padx=(0, 8))
        ttk.Entry(self.toolbar, textvariable=self.top_n_var, width=6).grid(row=0, column=14)

        self.content = ttk.Frame(self.main, style="App.TFrame")
        self.content.grid(row=2, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self._build_workspace_view()
        self._build_profile_view()
        self._build_kwic_view()
        self._build_lexicon_view()
        self._build_compare_view()
        self._build_help_view()

        self.footer = ttk.Frame(self.main, style="App.TFrame")
        self.footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(self.footer, textvariable=self.status_var, style="Subtle.TLabel").grid(row=0, column=0, sticky="w")

        self._switch_view("workspace")

    def _build_workspace_view(self) -> None:
        frame = ttk.Frame(self.content, style="App.TFrame")
        frame.columnconfigure(0, weight=4)
        frame.columnconfigure(1, weight=5)
        frame.rowconfigure(0, weight=1)
        self.view_frames["workspace"] = frame

        left = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.input_frame = left

        self.primary_text = tk.Text(
            left,
            wrap="word",
            font=("Yu Gothic UI", 11),
            background="#ffffff",
            foreground="#111827",
            relief="flat",
            padx=12,
            pady=12,
        )
        self.primary_text.grid(row=0, column=0, sticky="nsew")
        self.primary_text.tag_configure("highlight", background="#fff1a8", foreground="#111827")
        input_scroll = ttk.Scrollbar(left, orient="vertical", command=self.primary_text.yview)
        input_scroll.grid(row=0, column=1, sticky="ns")
        self.primary_text.configure(yscrollcommand=input_scroll.set)

        right = ttk.Frame(frame, style="App.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        stats_row = ttk.Frame(right, style="App.TFrame")
        stats_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for index in range(3):
            stats_row.columnconfigure(index, weight=1)
        self.token_stat = self._create_stat_card(stats_row, 0)
        self.lemma_stat = self._create_stat_card(stats_row, 1)
        self.domain_stat = self._create_stat_card(stats_row, 2)

        target_card = ttk.LabelFrame(right, style="Card.TLabelframe", padding=12)
        target_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        target_card.columnconfigure(1, weight=1)
        self.target_title = ttk.Label(target_card, style="StatTitle.TLabel")
        self.target_title.grid(row=0, column=0, sticky="w")
        self.target_value = ttk.Label(target_card, style="StatValue.TLabel")
        self.target_value.grid(row=0, column=1, sticky="w", padx=(10, 0))
        self.target_domain = ttk.Label(target_card, style="Subtle.TLabel")
        self.target_domain.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(4, 0))

        result_card = ttk.LabelFrame(right, style="Card.TLabelframe", padding=12)
        result_card.grid(row=2, column=0, sticky="nsew")
        result_card.columnconfigure(0, weight=1)
        result_card.rowconfigure(1, weight=1)
        self.result_frame = result_card

        self.summary_text = tk.Text(
            result_card,
            height=5,
            wrap="word",
            font=("Consolas", 10),
            background="#f8fafc",
            foreground="#24324b",
            relief="flat",
            padx=10,
            pady=8,
        )
        self.summary_text.grid(row=0, column=0, sticky="ew")

        self.result_tabs = ttk.Notebook(result_card)
        self.result_tabs.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.tokens_table = self._build_notebook_table(
            self.result_tabs,
            ("surface", "lemma", "pos", "domain_code", "domain_label"),
            (170, 170, 220, 110, 220),
        )
        self.lemma_table = self._build_notebook_table(self.result_tabs, ("lemma", "count"), (280, 100))
        self.domain_table = self._build_notebook_table(self.result_tabs, ("domain_code", "count"), (220, 100))
        self.json_output = tk.Text(
            self.result_tabs,
            wrap="none",
            font=("Consolas", 10),
            background="#ffffff",
            foreground="#111827",
            relief="flat",
            padx=10,
            pady=10,
        )
        self.result_tabs.add(self.json_output, text="")

        self.tokens_table.bind("<<TreeviewSelect>>", lambda _event: self._select_workspace_row(self.tokens_table, "token"))
        self.lemma_table.bind("<<TreeviewSelect>>", lambda _event: self._select_workspace_row(self.lemma_table, "lemma"))
        self.domain_table.bind("<<TreeviewSelect>>", lambda _event: self._select_workspace_row(self.domain_table, "domain"))
        self.tokens_table.bind("<Double-1>", lambda _event: self._switch_view("kwic"))
        self.lemma_table.bind("<Double-1>", lambda _event: self._switch_view("kwic"))
        self.domain_table.bind("<Double-1>", lambda _event: self._switch_view("profile"))
        self.tokens_table.bind("<Button-3>", lambda event: self._show_workspace_menu(event, self.tokens_table, "token"))
        self.lemma_table.bind("<Button-3>", lambda event: self._show_workspace_menu(event, self.lemma_table, "lemma"))
        self.domain_table.bind("<Button-3>", lambda event: self._show_workspace_menu(event, self.domain_table, "domain"))

    def _build_profile_view(self) -> None:
        frame = ttk.Frame(self.content, style="App.TFrame")
        frame.columnconfigure(0, weight=3)
        frame.columnconfigure(1, weight=3)
        frame.columnconfigure(2, weight=2)
        frame.rowconfigure(0, weight=1)
        self.view_frames["profile"] = frame

        left = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.profile_frame = left

        self.profile_domain_tree = ttk.Treeview(left, columns=("domain", "freq", "rel"), show="headings")
        self.profile_domain_tree.grid(row=0, column=0, sticky="nsew")
        profile_domain_scroll = ttk.Scrollbar(left, orient="vertical", command=self.profile_domain_tree.yview)
        profile_domain_scroll.grid(row=0, column=1, sticky="ns")
        self.profile_domain_tree.configure(yscrollcommand=profile_domain_scroll.set)

        mid = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        mid.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)
        self.domain_words_frame = mid

        self.profile_word_tree = ttk.Treeview(mid, columns=("word", "lemma", "freq", "rel", "cc"), show="headings")
        self.profile_word_tree.grid(row=0, column=0, sticky="nsew")
        profile_word_scroll = ttk.Scrollbar(mid, orient="vertical", command=self.profile_word_tree.yview)
        profile_word_scroll.grid(row=0, column=1, sticky="ns")
        self.profile_word_tree.configure(yscrollcommand=profile_word_scroll.set)

        right = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        right.grid(row=0, column=2, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.profile_summary_text = tk.Text(
            right,
            wrap="word",
            font=("Consolas", 10),
            relief="flat",
            background="#ffffff",
            foreground="#111827",
            padx=10,
            pady=10,
        )
        self.profile_summary_text.grid(row=0, column=0, sticky="nsew")

        self.profile_domain_tree.bind("<<TreeviewSelect>>", lambda _event: self._on_profile_domain_select())
        self.profile_domain_tree.bind("<Double-1>", lambda _event: self._open_domain_drilldown())
        self.profile_domain_tree.bind("<Button-3>", lambda event: self._show_profile_domain_menu(event))
        self.profile_word_tree.bind("<<TreeviewSelect>>", lambda _event: self._on_profile_word_select())
        self.profile_word_tree.bind("<Double-1>", lambda _event: self._open_kwic_from_profile())
        self.profile_word_tree.bind("<Button-3>", lambda event: self._show_profile_word_menu(event))

    def _build_kwic_view(self) -> None:
        frame = ttk.Frame(self.content, style="App.TFrame")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)
        self.view_frames["kwic"] = frame

        controls = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for index in range(8):
            controls.columnconfigure(index, weight=0)
        controls.columnconfigure(8, weight=1)

        self.kwic_keyword_label = ttk.Label(controls)
        self.kwic_keyword_label.grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(controls, textvariable=self.keyword_var, width=24).grid(row=0, column=1, padx=(0, 12))
        self.kwic_domain_label = ttk.Label(controls)
        self.kwic_domain_label.grid(row=0, column=2, padx=(0, 8))
        ttk.Entry(controls, textvariable=self.selected_domain_var, width=12).grid(row=0, column=3, padx=(0, 12))
        self.kwic_refresh_button = ttk.Button(controls, style="Primary.TButton", command=self._refresh_kwic_view)
        self.kwic_refresh_button.grid(row=0, column=4, padx=(0, 12))
        self.kwic_export_button = ttk.Button(controls, style="Ghost.TButton", command=self._export_current_kwic)
        self.kwic_export_button.grid(row=0, column=5)

        table_card = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        table_card.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(0, weight=1)

        self.kwic_tree = ttk.Treeview(
            table_card,
            columns=("line", "left", "key", "right", "domain", "offset"),
            show="headings",
            style="Kwic.Treeview",
        )
        self.kwic_tree.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(table_card, orient="vertical", command=self.kwic_tree.yview).grid(row=0, column=1, sticky="ns")

        preview_card = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        preview_card.grid(row=2, column=0, sticky="nsew")
        for index in range(3):
            preview_card.columnconfigure(index, weight=1)
        preview_card.rowconfigure(1, weight=1)

        self.prev_label = ttk.Label(preview_card)
        self.prev_label.grid(row=0, column=0, sticky="w")
        self.curr_label = ttk.Label(preview_card)
        self.curr_label.grid(row=0, column=1, sticky="w")
        self.next_label = ttk.Label(preview_card)
        self.next_label.grid(row=0, column=2, sticky="w")

        self.kwic_prev_text = tk.Text(preview_card, wrap="word", font=("Yu Gothic UI", 10), relief="flat", background="#ffffff")
        self.kwic_curr_text = tk.Text(preview_card, wrap="word", font=("Yu Gothic UI", 10), relief="flat", background="#ffffff")
        self.kwic_next_text = tk.Text(preview_card, wrap="word", font=("Yu Gothic UI", 10), relief="flat", background="#ffffff")
        for widget in (self.kwic_prev_text, self.kwic_curr_text, self.kwic_next_text):
            widget.tag_configure("highlight", background="#fff1a8", foreground="#111827")
        self.kwic_prev_text.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self.kwic_curr_text.grid(row=1, column=1, sticky="nsew", padx=6)
        self.kwic_next_text.grid(row=1, column=2, sticky="nsew", padx=(6, 0))

        self.kwic_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_kwic_preview())
        self.kwic_tree.bind("<Double-1>", lambda _event: self._open_kwic_detail_popup())
        self.kwic_tree.bind("<Button-3>", lambda event: self._show_kwic_menu(event))

    def _build_lexicon_view(self) -> None:
        frame = ttk.Frame(self.content, style="App.TFrame")
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=3)
        frame.rowconfigure(1, weight=1)
        self.view_frames["lexicon"] = frame

        controls = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.lexicon_domain_var = tk.StringVar(value=self.selected_domain_var.get().strip() or "F1")
        self.lexicon_term_var = tk.StringVar(value="")
        self.lexicon_note_label = ttk.Label(controls, style="Subtle.TLabel")
        self.lexicon_note_label.grid(row=0, column=0, columnspan=8, sticky="w", pady=(0, 8))
        ttk.Label(controls, textvariable=tk.StringVar(value="")).grid(row=1, column=0)
        self.lexicon_domain_label = ttk.Label(controls)
        self.lexicon_domain_label.grid(row=1, column=0, padx=(0, 8))
        ttk.Combobox(controls, textvariable=self.lexicon_domain_var, values=sorted(self.categories.keys()), width=16).grid(row=1, column=1, padx=(0, 10))
        self.lexicon_term_label = ttk.Label(controls)
        self.lexicon_term_label.grid(row=1, column=2, padx=(0, 8))
        ttk.Entry(controls, textvariable=self.lexicon_term_var, width=28).grid(row=1, column=3, padx=(0, 10))
        self.lexicon_add_button = ttk.Button(controls, style="Primary.TButton", command=self._add_single_lexicon_term)
        self.lexicon_add_button.grid(row=1, column=4, padx=(0, 8))
        self.lexicon_paste_button = ttk.Button(controls, style="Ghost.TButton", command=self._import_lexicon_from_text)
        self.lexicon_paste_button.grid(row=1, column=5, padx=(0, 8))
        self.lexicon_import_button = ttk.Button(controls, style="Ghost.TButton", command=self._import_lexicon_from_file)
        self.lexicon_import_button.grid(row=1, column=6, padx=(0, 8))
        self.lexicon_save_button = ttk.Button(controls, style="Ghost.TButton", command=self._save_lexicon)
        self.lexicon_save_button.grid(row=1, column=7)

        domains_card = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        domains_card.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        domains_card.columnconfigure(0, weight=1)
        domains_card.rowconfigure(0, weight=1)
        self.lexicon_domains_frame = domains_card

        self.lexicon_domain_tree = ttk.Treeview(domains_card, columns=("domain", "label", "count"), show="headings")
        self.lexicon_domain_tree.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(domains_card, orient="vertical", command=self.lexicon_domain_tree.yview).grid(row=0, column=1, sticky="ns")

        terms_card = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=10)
        terms_card.grid(row=1, column=1, sticky="nsew")
        terms_card.columnconfigure(0, weight=1)
        terms_card.rowconfigure(0, weight=1)
        self.lexicon_terms_frame = terms_card

        self.lexicon_term_tree = ttk.Treeview(terms_card, columns=("term",), show="headings")
        self.lexicon_term_tree.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(terms_card, orient="vertical", command=self.lexicon_term_tree.yview).grid(row=0, column=1, sticky="ns")

        term_actions = ttk.Frame(terms_card, style="App.TFrame")
        term_actions.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.lexicon_remove_term_button = ttk.Button(term_actions, style="Ghost.TButton", command=self._remove_selected_lexicon_term)
        self.lexicon_remove_term_button.pack(side="left")
        self.lexicon_remove_domain_button = ttk.Button(term_actions, style="Ghost.TButton", command=self._remove_selected_lexicon_domain)
        self.lexicon_remove_domain_button.pack(side="left", padx=(8, 0))
        self.lexicon_tagger_button = ttk.Button(term_actions, style="Ghost.TButton", command=self._open_semantic_tagger_popup)
        self.lexicon_tagger_button.pack(side="left", padx=(8, 0))

        self.lexicon_domain_tree.bind("<<TreeviewSelect>>", lambda _event: self._refresh_lexicon_terms())
        self.lexicon_term_tree.bind("<Button-3>", lambda event: self._show_lexicon_term_menu(event))

    def _build_compare_view(self) -> None:
        frame = ttk.Frame(self.content, style="App.TFrame")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        self.view_frames["compare"] = frame

        editors = ttk.Frame(frame, style="App.TFrame")
        editors.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        editors.columnconfigure(0, weight=1)
        editors.columnconfigure(1, weight=1)

        left_frame = ttk.LabelFrame(editors, style="Card.TLabelframe", padding=10)
        right_frame = ttk.LabelFrame(editors, style="Card.TLabelframe", padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        self.left_text_frame = left_frame
        self.right_text_frame = right_frame

        self.compare_left_text = tk.Text(left_frame, wrap="word", height=10, font=("Yu Gothic UI", 10), relief="flat", background="#ffffff")
        self.compare_right_text = tk.Text(right_frame, wrap="word", height=10, font=("Yu Gothic UI", 10), relief="flat", background="#ffffff")
        self.compare_left_text.grid(row=0, column=0, sticky="nsew")
        self.compare_right_text.grid(row=0, column=0, sticky="nsew")

        actions = ttk.Frame(frame, style="App.TFrame")
        actions.grid(row=1, column=0, sticky="nsew")
        actions.columnconfigure(0, weight=1)
        actions.rowconfigure(1, weight=1)
        self.compare_run_button = ttk.Button(actions, style="Primary.TButton", command=self._run_compare)
        self.compare_run_button.grid(row=0, column=0, sticky="w")

        self.compare_tabs = ttk.Notebook(actions)
        self.compare_tabs.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.compare_lemma_table = self._build_notebook_table(self.compare_tabs, ("key", "left_count", "right_count", "delta"), (260, 110, 110, 110))
        self.compare_domain_table = self._build_notebook_table(self.compare_tabs, ("key", "left_count", "right_count", "delta"), (220, 110, 110, 110))

    def _build_help_view(self) -> None:
        frame = ttk.Frame(self.content, style="App.TFrame")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.view_frames["help"] = frame

        card = ttk.LabelFrame(frame, style="Card.TLabelframe", padding=12)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.help_text = tk.Text(
            card,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            background="#ffffff",
            foreground="#111827",
            padx=12,
            pady=12,
        )
        self.help_text.grid(row=0, column=0, sticky="nsew")

    def _build_menubar(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=tr(self.current_language, "open_txt"), command=self._open_text_file)
        file_menu.add_command(label=tr(self.current_language, "save_project"), command=self._save_project)
        file_menu.add_command(label=tr(self.current_language, "open_project"), command=self._open_project)
        file_menu.add_separator()
        file_menu.add_command(label=tr(self.current_language, "export_json"), command=self._export_json)
        file_menu.add_command(label=tr(self.current_language, "export_csv"), command=self._export_csv)
        file_menu.add_command(label=tr(self.current_language, "export_bundle"), command=self._export_bundle)
        file_menu.add_separator()
        file_menu.add_command(label=tr(self.current_language, "clear"), command=self._clear_primary)
        menubar.add_cascade(label=self._t("menu_file"), menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label=self._t("workspace"), command=lambda: self._switch_view("workspace"))
        view_menu.add_command(label=self._t("profile"), command=lambda: self._switch_view("profile"))
        view_menu.add_command(label=self._t("kwic"), command=lambda: self._switch_view("kwic"))
        view_menu.add_command(label=self._t("lexicon_center"), command=lambda: self._switch_view("lexicon"))
        view_menu.add_command(label=self._t("compare_center"), command=lambda: self._switch_view("compare"))
        menubar.add_cascade(label=self._t("menu_view"), menu=view_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label=tr(self.current_language, "analyze"), command=self._analyze_primary)
        tools_menu.add_command(label=self._t("semantic_tagger"), command=self._open_semantic_tagger_popup)
        tools_menu.add_command(label=tr(self.current_language, "edit_lexicon"), command=lambda: self._switch_view("lexicon"))
        tools_menu.add_command(label=tr(self.current_language, "compare"), command=lambda: self._switch_view("compare"))
        menubar.add_cascade(label=self._t("menu_tools"), menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=self._t("help_center"), command=lambda: self._switch_view("help"))
        help_menu.add_command(label=self._t("about"), command=self._open_about_popup)
        menubar.add_cascade(label=self._t("menu_help"), menu=help_menu)

        self.root.config(menu=menubar)

    def _apply_language(self) -> None:
        self.root.title(tr(self.current_language, "app_title"))
        self.sidebar_subtitle.configure(text=self._t("subtitle"))
        self.header_subtitle.configure(text=self._t("subtitle"))
        self.open_button.configure(text=self._t("open"))
        self.analyze_button.configure(text=tr(self.current_language, "analyze"))
        self.save_project_button.configure(text=self._t("save_project_short"))
        self.export_button.configure(text=self._t("export"))
        self.lexicon_label.configure(text=tr(self.current_language, "lexicon"))
        self.browse_button.configure(text=tr(self.current_language, "browse"))
        self.language_label.configure(text=tr(self.current_language, "language"))
        self.mode_label.configure(text=tr(self.current_language, "mode"))
        self.min_freq_label.configure(text=tr(self.current_language, "min_freq"))
        self.top_n_label.configure(text=tr(self.current_language, "top_n"))

        for view_key, button in self.nav_buttons.items():
            button.configure(text=self._t(getattr(self, f"{view_key}_nav_label_key")))

        self.input_frame.configure(text=tr(self.current_language, "input_text"))
        self.result_frame.configure(text=tr(self.current_language, "analysis_result"))
        self.result_tabs.tab(0, text=tr(self.current_language, "tokens"))
        self.result_tabs.tab(1, text=tr(self.current_language, "lemma_frequency"))
        self.result_tabs.tab(2, text=tr(self.current_language, "domain_frequency"))
        self.result_tabs.tab(3, text=tr(self.current_language, "json_preview"))
        self.token_stat[0].configure(text="Tokens")
        self.lemma_stat[0].configure(text="Lemmas")
        self.domain_stat[0].configure(text="Domains")
        self.target_title.configure(text=self._t("current_target"))

        self._set_table_headings(
            self.tokens_table,
            {
                "surface": tr(self.current_language, "surface"),
                "lemma": tr(self.current_language, "lemma"),
                "pos": tr(self.current_language, "pos"),
                "domain_code": tr(self.current_language, "domain_code"),
                "domain_label": tr(self.current_language, "domain_label"),
            },
        )
        self._set_table_headings(self.lemma_table, {"lemma": tr(self.current_language, "lemma"), "count": tr(self.current_language, "count")})
        self._set_table_headings(self.domain_table, {"domain_code": tr(self.current_language, "domain_code"), "count": tr(self.current_language, "count")})

        self.profile_frame.configure(text=self._t("profile"))
        self.domain_words_frame.configure(text=self._t("domain_words"))
        self._set_table_headings(
            self.profile_domain_tree,
            {"domain": tr(self.current_language, "domain_code"), "freq": tr(self.current_language, "count"), "rel": self._t("relative_10k")},
        )
        self._set_table_headings(
            self.profile_word_tree,
            {"word": "Word", "lemma": tr(self.current_language, "lemma"), "freq": tr(self.current_language, "count"), "rel": self._t("relative_10k"), "cc": self._t("kwic")},
        )

        self.kwic_keyword_label.configure(text=tr(self.current_language, "search_keyword"))
        self.kwic_domain_label.configure(text=self._t("domain_filter"))
        self.kwic_refresh_button.configure(text=self._t("refresh"))
        self.kwic_export_button.configure(text=self._t("export"))
        self._set_table_headings(
            self.kwic_tree,
            {
                "line": self._t("line"),
                "left": self._t("left_context"),
                "key": "Key",
                "right": self._t("right_context"),
                "domain": tr(self.current_language, "domain_code"),
                "offset": self._t("source_offset"),
            },
        )
        self.kwic_tree.column("line", width=70, anchor="center")
        self.kwic_tree.column("left", width=360, anchor="e")
        self.kwic_tree.column("key", width=170, anchor="center")
        self.kwic_tree.column("right", width=360, anchor="w")
        self.kwic_tree.column("domain", width=0, minwidth=0, stretch=False)
        self.kwic_tree.column("offset", width=0, minwidth=0, stretch=False)
        self.prev_label.configure(text=tr(self.current_language, "previous_sentence"))
        self.curr_label.configure(text=tr(self.current_language, "current_sentence"))
        self.next_label.configure(text=tr(self.current_language, "next_sentence"))

        self.lexicon_note_label.configure(text=self._t("lemma_note"))
        self.lexicon_domain_label.configure(text=tr(self.current_language, "domain_code"))
        self.lexicon_term_label.configure(text=tr(self.current_language, "lemma"))
        self.lexicon_add_button.configure(text=tr(self.current_language, "add_term"))
        self.lexicon_paste_button.configure(text=self._t("import_text"))
        self.lexicon_import_button.configure(text=self._t("import_file"))
        self.lexicon_save_button.configure(text=tr(self.current_language, "save"))
        self.lexicon_domains_frame.configure(text=self._t("lexicon_domains"))
        self.lexicon_terms_frame.configure(text=self._t("lexicon_terms"))
        self._set_table_headings(
            self.lexicon_domain_tree,
            {"domain": tr(self.current_language, "domain_code"), "label": tr(self.current_language, "domain_label"), "count": tr(self.current_language, "count")},
        )
        self._set_table_headings(self.lexicon_term_tree, {"term": tr(self.current_language, "lemma")})
        self.lexicon_remove_term_button.configure(text=self._t("remove_term"))
        self.lexicon_remove_domain_button.configure(text=self._t("remove_domain"))
        self.lexicon_tagger_button.configure(text=self._t("semantic_tagger"))

        self.left_text_frame.configure(text=tr(self.current_language, "left_text"))
        self.right_text_frame.configure(text=tr(self.current_language, "right_text"))
        self.compare_run_button.configure(text=tr(self.current_language, "compare"))
        self.compare_tabs.tab(0, text=tr(self.current_language, "compare_lemma"))
        self.compare_tabs.tab(1, text=tr(self.current_language, "compare_domain"))

        self.help_text.configure(state="normal")
        self.help_text.delete("1.0", tk.END)
        self.help_text.insert("1.0", f"{self._t('help_text')}\n\n{self._t('about_text')}")
        self.help_text.configure(state="disabled")

        self._build_menubar()
        self._sync_target_display()
        self._refresh_lexicon_view()
        if self.last_result:
            self._refresh_profile_view()
            self._refresh_kwic_view()

    def _on_language_changed(self) -> None:
        self._apply_language()

    def _switch_view(self, view_key: str) -> None:
        for key, frame in self.view_frames.items():
            frame.grid_forget()
        self.view_frames[view_key].grid(row=0, column=0, sticky="nsew")
        self.current_view_var.set(view_key)
        self.status_var.set(f"{self._t('switch_done')}: {self._t(getattr(self, f'{view_key}_nav_label_key', view_key))}")

        if view_key == "profile" and self.last_result:
            self._refresh_profile_view()
        elif view_key == "kwic" and self.last_result:
            self._refresh_kwic_view()
        elif view_key == "lexicon":
            self._refresh_lexicon_view()
        elif view_key == "compare":
            self._prefill_compare_texts()

    def _create_stat_card(self, parent: ttk.Frame, column: int) -> tuple[ttk.Label, ttk.Label]:
        card = ttk.LabelFrame(parent, style="Card.TLabelframe", padding=12)
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
        title = ttk.Label(card, style="StatTitle.TLabel")
        title.grid(row=0, column=0, sticky="w")
        value = ttk.Label(card, style="StatValue.TLabel")
        value.grid(row=1, column=0, sticky="w", pady=(6, 0))
        return title, value

    def _build_notebook_table(self, notebook: ttk.Notebook, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(notebook, style="Surface.TFrame")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        notebook.add(frame, text="")
        table = ttk.Treeview(frame, columns=columns, show="headings")
        for column, width in zip(columns, widths):
            table.heading(column, text=column)
            table.column(column, width=width, anchor="w")
        table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        table.configure(yscrollcommand=scroll.set)
        return table

    @staticmethod
    def _set_table_headings(table: ttk.Treeview, headings: dict[str, str]) -> None:
        for column, label in headings.items():
            table.heading(column, text=label)

    def _load_sample_if_present(self) -> None:
        sample_path = self.base_dir / "sample.txt"
        if sample_path.exists():
            try:
                self.primary_text.insert("1.0", read_text_file(str(sample_path)))
            except OSError:
                return

    def _refresh_status_ready(self) -> None:
        self.status_var.set(tr(self.current_language, "status_ready"))
        if self.last_result is None:
            self.token_stat[1].configure(text="0")
            self.lemma_stat[1].configure(text="0")
            self.domain_stat[1].configure(text="0")
            self.target_value.configure(text="-")
            self.target_domain.configure(text="")

    def _choose_lexicon(self) -> None:
        selected = filedialog.askopenfilename(
            title=tr(self.current_language, "lexicon"),
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialdir=str(self.default_lexicon.parent),
        )
        if not selected:
            return
        self.lexicon_var.set(selected)
        self.recent_files["recent_lexicon_files"] = push_recent_file(self.recent_files.get("recent_lexicon_files", []), selected)
        self._save_recent_files()
        self._refresh_lexicon_view()

    def _open_text_file(self) -> None:
        selected = filedialog.askopenfilename(
            title=tr(self.current_language, "open_txt"),
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialdir=str(self.base_dir),
        )
        if selected:
            self._load_text_into_widget(Path(selected))

    def _load_text_into_widget(self, path: Path) -> None:
        try:
            content = read_text_file(str(path))
        except Exception as exc:
            messagebox.showerror(tr(self.current_language, "open_failed"), str(exc))
            return
        self.primary_text.delete("1.0", tk.END)
        self.primary_text.insert("1.0", content)
        self._highlight_text_widget(self.primary_text, self.keyword_var.get().strip())
        self.recent_files["recent_text_files"] = push_recent_file(self.recent_files.get("recent_text_files", []), str(path))
        self._save_recent_files()
        self.status_var.set(f"{tr(self.current_language, 'open_txt')}: {path.name}")

    def _read_numeric_options(self) -> tuple[int, int | None]:
        return parse_numeric_options(
            self.min_freq_var.get(),
            self.top_n_var.get(),
        )

    def _set_busy(self, busy: bool) -> None:
        """Disable primary action buttons during long analysis/compare."""
        state = ("disabled",) if busy else ("!disabled",)
        for widget in (
            getattr(self, "analyze_button", None),
            getattr(self, "kwic_refresh_button", None),
            getattr(self, "compare_run_button", None),
            getattr(self, "kwic_export_button", None),
        ):
            if widget is not None:
                try:
                    widget.state(state)
                except tk.TclError:
                    pass

    def _begin_busy(self) -> None:
        self._busy_depth += 1
        if self._busy_depth == 1:
            self._set_busy(True)

    def _end_busy(self) -> None:
        self._busy_depth = max(0, self._busy_depth - 1)
        if self._busy_depth == 0:
            self._set_busy(False)

    def _run_analysis(self, text: str) -> dict:
        return run_analysis(
            text=text,
            lexicon_path=self.lexicon_var.get().strip(),
            categories_path=str(self.categories_path),
            categories=self.categories,
            language=self.current_language,
            mode=self.mode_var.get().strip(),
            unknown_domain=self.unknown_domain_var.get().strip(),
            min_frequency_raw=self.min_freq_var.get(),
            top_n_raw=self.top_n_var.get(),
        )

    def _analyze_primary(self) -> None:
        text = self.primary_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning(tr(self.current_language, "analysis_failed"), tr(self.current_language, "no_text"))
            return
        self._begin_busy()
        try:
            try:
                self.last_result = self._run_analysis(text)
            except Exception as exc:
                messagebox.showerror(tr(self.current_language, "analysis_failed"), str(exc))
                self.status_var.set(tr(self.current_language, "analysis_failed"))
                return
        finally:
            self._end_busy()

        self._render_analysis_result(self.last_result)
        self._refresh_profile_view()
        self._refresh_kwic_view()
        self._refresh_lexicon_view()
        self._highlight_text_widget(self.primary_text, self.keyword_var.get().strip())
        summary = self.last_result.get("summary", {})
        self.token_stat[1].configure(text=str(summary.get("token_count", 0)))
        self.lemma_stat[1].configure(text=str(summary.get("unique_lemma_count", 0)))
        self.domain_stat[1].configure(text=str(summary.get("unique_domain_count", 0)))
        self.status_var.set(f"{tr(self.current_language, 'analyze')}: {summary.get('token_count', 0)} tokens")

    def _render_analysis_result(self, result: dict) -> None:
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", "\n".join(f"{key}: {value}" for key, value in result.get("summary", {}).items()))
        self._fill_table(
            self.tokens_table,
            [(item["surface"], item["lemma"], item["pos"], item["domain_code"], item["domain_label"]) for item in result.get("tokens", [])],
        )
        self._fill_table(self.lemma_table, [(lemma, count) for lemma, count in result.get("lemma_frequency", {}).items()])
        self._fill_table(self.domain_table, [(domain, count) for domain, count in result.get("domain_frequency", {}).items()])
        self.json_output.delete("1.0", tk.END)
        self.json_output.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2))

    def _sync_target_display(self) -> None:
        word = self.keyword_var.get().strip()
        domain = self.selected_domain_var.get().strip()
        self.target_value.configure(text=word or "-")
        if domain:
            info = self.categories.get(domain, {})
            label = info.get(self.current_language, info.get("en", domain)) if isinstance(info, dict) else domain
            self.target_domain.configure(text=f"{domain}  {label}")
        else:
            self.target_domain.configure(text="")
        if word:
            self._highlight_text_widget(self.primary_text, word)

    def _select_workspace_row(self, table: ttk.Treeview, kind: str) -> None:
        selection = table.selection()
        if not selection:
            return
        values = table.item(selection[0], "values")
        if not values:
            return
        if kind == "token":
            self.keyword_var.set(str(values[1]))
            self.selected_domain_var.set(str(values[3]))
        elif kind == "lemma":
            self.keyword_var.set(str(values[0]))
        elif kind == "domain":
            self.selected_domain_var.set(str(values[0]))
        self._sync_target_display()

    def _show_workspace_menu(self, event: tk.Event, table: ttk.Treeview, kind: str) -> None:
        row_id = table.identify_row(event.y)
        if row_id:
            table.selection_set(row_id)
        selection = table.selection()
        if not selection:
            return
        values = table.item(selection[0], "values")
        if not values:
            return
        if kind == "token":
            self.keyword_var.set(str(values[1]))
            self.selected_domain_var.set(str(values[3]))
        elif kind == "lemma":
            self.keyword_var.set(str(values[0]))
        elif kind == "domain":
            self.selected_domain_var.set(str(values[0]))
        self._sync_target_display()

        menu = tk.Menu(table, tearoff=0)
        menu.add_command(label=self._t("view_kwic"), command=lambda: self._switch_view("kwic"))
        menu.add_command(label=self._t("view_domain_words"), command=lambda: self._switch_view("profile"))
        menu.add_command(label=self._t("view_in_lexicon"), command=lambda: self._switch_view("lexicon"))
        menu.add_command(label=self._t("add_to_current_domain"), command=lambda: self._lexicon_add_term(self.keyword_var.get().strip(), self.selected_domain_var.get().strip()))
        menu.add_command(label=self._t("move_to_domain"), command=lambda: self._move_term_dialog(self.keyword_var.get().strip(), self.selected_domain_var.get().strip()))
        menu.tk_popup(event.x_root, event.y_root)

    def _refresh_profile_view(self) -> None:
        if not self.last_result:
            self._fill_table(self.profile_domain_tree, [])
            self._fill_table(self.profile_word_tree, [])
            self.profile_summary_text.delete("1.0", tk.END)
            return

        rows = build_profile_rows(
            tokens=self.last_result.get("tokens", []),
            categories=self.categories,
            language=self.current_language,
        )
        self.profile_domain_map.clear()
        for item_id in self.profile_domain_tree.get_children():
            self.profile_domain_tree.delete(item_id)
        for row in rows:
            item_id = self.profile_domain_tree.insert("", tk.END, values=(row["domain_code"], row["frequency"], row["relative_per_10k"]))
            self.profile_domain_map[item_id] = row
        if rows:
            children = self.profile_domain_tree.get_children()
            selected = None
            for child in children:
                if self.profile_domain_tree.item(child, "values")[0] == self.selected_domain_var.get().strip():
                    selected = child
                    break
            self.profile_domain_tree.selection_set(selected or children[0])
            self._on_profile_domain_select()

    def _on_profile_domain_select(self) -> None:
        selection = self.profile_domain_tree.selection()
        if not selection or not self.last_result:
            return
        row = self.profile_domain_map.get(selection[0])
        if not row:
            return
        code = str(row["domain_code"])
        self.selected_domain_var.set(code)
        self._sync_target_display()

        self._fill_table(self.profile_word_tree, build_domain_word_table_rows(self.last_result.get("tokens", []), code))

        self.profile_summary_text.delete("1.0", tk.END)
        lines = build_profile_summary_lines(
            row,
            tr_fn=tr,
            extra_t_fn=self._t,
            language=self.current_language,
        )
        self.profile_summary_text.insert("1.0", "\n".join(lines) + "\n")

    def _on_profile_word_select(self) -> None:
        selection = self.profile_word_tree.selection()
        if not selection:
            return
        values = self.profile_word_tree.item(selection[0], "values")
        if values:
            self.keyword_var.set(str(values[1]))
            self._sync_target_display()

    def _open_kwic_from_profile(self) -> None:
        self._on_profile_word_select()
        self._switch_view("kwic")

    def _open_domain_drilldown(self) -> None:
        selection = self.profile_domain_tree.selection()
        if not selection:
            return
        row = self.profile_domain_map.get(selection[0])
        if not row:
            return
        popup = tk.Toplevel(self.root)
        popup.title(f"{self._t('domain_words')} - {row['domain_code']}")
        popup.geometry("900x640")
        popup.transient(self.root)
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(0, weight=1)

        table = ttk.Treeview(popup, columns=("word", "lemma", "freq", "rel", "cc"), show="headings")
        self._set_table_headings(
            table,
            {"word": "Word", "lemma": tr(self.current_language, "lemma"), "freq": tr(self.current_language, "count"), "rel": self._t("relative_10k"), "cc": self._t("kwic")},
        )
        table.column("word", width=170, anchor="w")
        table.column("lemma", width=200, anchor="w")
        table.column("freq", width=100, anchor="center")
        table.column("rel", width=110, anchor="center")
        table.column("cc", width=110, anchor="center")
        table.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(popup, orient="vertical", command=table.yview).grid(row=0, column=1, sticky="ns")

        rows = build_domain_word_table_rows(self.last_result.get("tokens", []), str(row["domain_code"]))
        self._fill_table(table, rows)
        table.bind("<<TreeviewSelect>>", lambda _event: self._select_domain_drilldown_word(table))
        table.bind("<Double-1>", lambda _event: (self._select_domain_drilldown_word(table), self._switch_view("kwic"), popup.destroy()))

    def _select_domain_drilldown_word(self, table: ttk.Treeview) -> None:
        selection = table.selection()
        if not selection:
            return
        values = table.item(selection[0], "values")
        if values:
            self.keyword_var.set(str(values[1]))
            self._sync_target_display()

    def _show_profile_domain_menu(self, event: tk.Event) -> None:
        row_id = self.profile_domain_tree.identify_row(event.y)
        if row_id:
            self.profile_domain_tree.selection_set(row_id)
            self._on_profile_domain_select()
        selection = self.profile_domain_tree.selection()
        if not selection:
            return
        menu = tk.Menu(self.profile_domain_tree, tearoff=0)
        menu.add_command(label=self._t("view_domain_words"), command=self._open_domain_drilldown)
        menu.add_command(label=self._t("view_kwic"), command=lambda: self._switch_view("kwic"))
        menu.tk_popup(event.x_root, event.y_root)

    def _show_profile_word_menu(self, event: tk.Event) -> None:
        row_id = self.profile_word_tree.identify_row(event.y)
        if row_id:
            self.profile_word_tree.selection_set(row_id)
            self._on_profile_word_select()
        selection = self.profile_word_tree.selection()
        if not selection:
            return
        menu = tk.Menu(self.profile_word_tree, tearoff=0)
        menu.add_command(label=self._t("view_kwic"), command=lambda: self._switch_view("kwic"))
        menu.add_command(label=self._t("add_to_current_domain"), command=lambda: self._lexicon_add_term(self.keyword_var.get().strip(), self.selected_domain_var.get().strip()))
        menu.add_command(label=self._t("view_in_lexicon"), command=lambda: self._switch_view("lexicon"))
        menu.tk_popup(event.x_root, event.y_root)

    def _refresh_kwic_view(self) -> None:
        if not self.last_result:
            self.kwic_rows = []
            self._fill_table(self.kwic_tree, [])
            self.status_var.set(tr(self.current_language, "no_analysis"))
            return
        keyword = self.keyword_var.get().strip()
        if not keyword:
            self.kwic_rows = []
            self._fill_table(self.kwic_tree, [])
            self.status_var.set(self._t("kwic_need_keyword"))
            return
        self.kwic_rows = kwic_from_result(
            self.last_result,
            keyword=keyword,
            domain_code=self.selected_domain_var.get().strip(),
            span=36,
        )
        self._fill_table(
            self.kwic_tree,
            [(row["line"], row["left"], row["key"], row["right"], row["domain_code"], row["source_offset"]) for row in self.kwic_rows],
        )
        if self.kwic_tree.get_children():
            self.kwic_tree.selection_set(self.kwic_tree.get_children()[0])
            self._update_kwic_preview()

    def _update_kwic_preview(self) -> None:
        selection = self.kwic_tree.selection()
        if not selection:
            return
        row_index = self.kwic_tree.index(selection[0])
        if row_index >= len(self.kwic_rows):
            return
        row = self.kwic_rows[row_index]
        self.selected_domain_var.set(str(row.get("domain_code", "")))
        self._sync_target_display()

        for widget, text_value, mark in (
            (self.kwic_prev_text, row.get("previous", ""), ""),
            (self.kwic_curr_text, row.get("current", ""), row.get("key", "")),
            (self.kwic_next_text, row.get("next", ""), ""),
        ):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", text_value)
            widget.tag_remove("highlight", "1.0", tk.END)
            if mark:
                start = "1.0"
                while True:
                    start = widget.search(mark, start, stopindex=tk.END)
                    if not start:
                        break
                    end = f"{start}+{len(mark)}c"
                    widget.tag_add("highlight", start, end)
                    start = end

    def _open_kwic_detail_popup(self) -> None:
        selection = self.kwic_tree.selection()
        if not selection or not self.last_result:
            return
        row_index = self.kwic_tree.index(selection[0])
        if row_index >= len(self.kwic_rows):
            return
        row = self.kwic_rows[row_index]
        detail = build_context_detail(self.last_result.get("source_text", ""), int(row["source_offset"]), str(row["key"]), window=180)

        popup = tk.Toplevel(self.root)
        popup.title(self._t("detail_popup"))
        popup.geometry("920x560")
        popup.transient(self.root)
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(1, weight=1)

        top = ttk.Frame(popup, style="App.TFrame", padding=12)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text=self._t("detail_popup"), style="Header.TLabel").pack(side="left")
        meta = f"{tr(self.current_language, 'domain_code')}: {row['domain_code']}   {self._t('source_offset')}: {row['source_offset']}   {self._t('confidence')}: {row['confidence']}"
        ttk.Label(top, text=meta, style="Subtle.TLabel").pack(side="left", padx=(14, 0))

        body = tk.Text(popup, wrap="word", font=("Yu Gothic UI", 11), relief="flat", background="#ffffff", padx=12, pady=10)
        body.tag_configure("hit", background="#ffe28a", foreground="#111827")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        body.insert("1.0", detail["snippet"])
        start_idx = body.index(f"1.0+{detail['highlight_start']}c")
        end_idx = body.index(f"1.0+{detail['highlight_end']}c")
        body.tag_add("hit", start_idx, end_idx)

    def _show_kwic_menu(self, event: tk.Event) -> None:
        row_id = self.kwic_tree.identify_row(event.y)
        if row_id:
            self.kwic_tree.selection_set(row_id)
        selection = self.kwic_tree.selection()
        if not selection:
            return
        row_index = self.kwic_tree.index(selection[0])
        if row_index >= len(self.kwic_rows):
            return
        row = self.kwic_rows[row_index]

        menu = tk.Menu(self.kwic_tree, tearoff=0)
        menu.add_command(label=self._t("copy_row"), command=lambda: self._copy_kwic_row(row))
        menu.add_command(label=self._t("jump_source"), command=self._open_kwic_detail_popup)
        menu.add_command(label=self._t("add_to_current_domain"), command=lambda: self._lexicon_add_term(str(row["key"]), str(row["domain_code"])))
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_kwic_row(self, row: dict) -> None:
        payload = f"{row['line']}\t{row['left']}\t{row['key']}\t{row['right']}"
        self.root.clipboard_clear()
        self.root.clipboard_append(payload)

    def _export_current_kwic(self) -> None:
        if not self.kwic_rows:
            messagebox.showinfo(tr(self.current_language, "export_failed"), self._t("kwic_export_empty"))
            self.status_var.set(self._t("kwic_export_empty"))
            return
        output = filedialog.asksaveasfilename(
            title=self._t("export"),
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not output:
            return
        try:
            with Path(output).open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["line", "left_context", "key", "right_context", "domain_code", "source_offset"])
                for row in self.kwic_rows:
                    writer.writerow([row["line"], row["left"], row["key"], row["right"], row["domain_code"], row["source_offset"]])
        except OSError as exc:
            messagebox.showerror(tr(self.current_language, "export_failed"), str(exc))
            self.status_var.set(tr(self.current_language, "export_failed"))
            return
        self.status_var.set(f"{self._t('kwic_export_saved')}: {output}")

    def _prefill_compare_texts(self) -> None:
        if not self.compare_left_text.get("1.0", tk.END).strip():
            self.compare_left_text.insert("1.0", self.primary_text.get("1.0", tk.END).strip())
        if self.left_result:
            self.compare_left_text.delete("1.0", tk.END)
            self.compare_left_text.insert("1.0", self.left_result.get("source_text", ""))
        if self.right_result:
            self.compare_right_text.delete("1.0", tk.END)
            self.compare_right_text.insert("1.0", self.right_result.get("source_text", ""))

    def _run_compare(self) -> None:
        left_source = self.compare_left_text.get("1.0", tk.END).strip()
        right_source = self.compare_right_text.get("1.0", tk.END).strip()
        if not left_source or not right_source:
            messagebox.showwarning(tr(self.current_language, "analysis_failed"), self._t("compare_need_both"))
            self.status_var.set(self._t("compare_need_both"))
            return
        self._begin_busy()
        try:
            self.left_result = self._run_analysis(left_source)
            self.right_result = self._run_analysis(right_source)
            comparison = build_comparison(self.left_result, self.right_result)
        except Exception as exc:
            messagebox.showerror(tr(self.current_language, "analysis_failed"), str(exc))
            self.status_var.set(tr(self.current_language, "analysis_failed"))
            return
        finally:
            self._end_busy()
        self._fill_table(
            self.compare_lemma_table,
            [(item["key"], item["left_count"], item["right_count"], item["delta"]) for item in comparison.get("lemma_comparison", [])],
        )
        self._fill_table(
            self.compare_domain_table,
            [(item["key"], item["left_count"], item["right_count"], item["delta"]) for item in comparison.get("domain_comparison", [])],
        )

    def _load_lexicon_data(self) -> dict:
        payload = read_json_file(self.lexicon_var.get().strip())
        if not isinstance(payload, dict):
            raise ValueError("Lexicon JSON must be object")
        return payload

    def _refresh_lexicon_view(self) -> None:
        try:
            lexicon_data = self._load_lexicon_data()
        except Exception:
            return
        self.lexicon_data = lexicon_data
        for item_id in self.lexicon_domain_tree.get_children():
            self.lexicon_domain_tree.delete(item_id)
        for code in sorted(lexicon_data):
            label = self.categories.get(code, {}).get(self.current_language, self.categories.get(code, {}).get("en", code))
            self.lexicon_domain_tree.insert("", tk.END, iid=code, values=(code, label, len(lexicon_data[code])))
        selected = self.lexicon_domain_var.get().strip()
        if selected in lexicon_data:
            self.lexicon_domain_tree.selection_set(selected)
        elif self.lexicon_domain_tree.get_children():
            self.lexicon_domain_tree.selection_set(self.lexicon_domain_tree.get_children()[0])
        self._refresh_lexicon_terms()

    def _refresh_lexicon_terms(self) -> None:
        for item_id in self.lexicon_term_tree.get_children():
            self.lexicon_term_tree.delete(item_id)
        selection = self.lexicon_domain_tree.selection()
        if not selection:
            return
        code = selection[0]
        self.lexicon_domain_var.set(code)
        self.selected_domain_var.set(code)
        self._sync_target_display()
        for term in sorted(self.lexicon_data.get(code, [])):
            self.lexicon_term_tree.insert("", tk.END, values=(term,))

    def _add_single_lexicon_term(self) -> None:
        self._lexicon_add_term(self.lexicon_term_var.get().strip(), self.lexicon_domain_var.get().strip())
        self.lexicon_term_var.set("")
        self._refresh_lexicon_view()

    def _parse_bulk_text(self, raw: str, fallback_domain: str) -> list[tuple[str, str]]:
        """Return (lemma, domain_code) pairs for _bulk_add_lemmas."""
        rows: list[tuple[str, str]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if "\t" in line:
                code, term = line.split("\t", 1)
            elif "," in line:
                code, term = line.split(",", 1)
            elif ":" in line:
                code, term = line.split(":", 1)
            else:
                code, term = fallback_domain, line
            code = code.strip() or fallback_domain
            term = term.strip()
            if term:
                rows.append((term, code))
        return rows

    def _import_lexicon_from_text(self) -> None:
        raw = simpledialog.askstring(
            self._t("batch_import"),
            "Use one term per line, or DOMAIN<TAB>TERM.",
            parent=self.root,
        )
        if not raw:
            return
        self._bulk_add_lemmas(self._parse_bulk_text(raw, self.lexicon_domain_var.get().strip() or "F1"))
        self._refresh_lexicon_view()

    def _import_lexicon_from_file(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._t("import_file"),
            filetypes=[("Text/CSV/JSON", "*.txt *.csv *.json"), ("All Files", "*.*")],
            initialdir=str(self.base_dir),
        )
        if not selected:
            return
        path = Path(selected)
        rows: list[tuple[str, str]] = []
        if path.suffix.lower() == ".json":
            payload = read_json_file(str(path))
            if isinstance(payload, dict):
                for code, words in payload.items():
                    if isinstance(words, list):
                        for word in words:
                            if isinstance(word, str):
                                rows.append((word.strip(), str(code)))
        else:
            raw = read_text_file(str(path))
            if path.suffix.lower() == ".csv":
                fb = self.lexicon_domain_var.get().strip() or "F1"
                for parsed in csv.reader(raw.splitlines()):
                    if not parsed:
                        continue
                    if len(parsed) >= 2:
                        rows.append((parsed[1].strip(), parsed[0].strip() or fb))
                    else:
                        rows.append((parsed[0].strip(), fb))
            else:
                rows = self._parse_bulk_text(raw, self.lexicon_domain_var.get().strip() or "F1")
        self._bulk_add_lemmas(rows)
        self._refresh_lexicon_view()

    def _save_lexicon(self) -> None:
        write_json(self.lexicon_data, Path(self.lexicon_var.get().strip()))
        self.status_var.set(self._t("lexicon_saved"))

    def _remove_selected_lexicon_term(self) -> None:
        selection = self.lexicon_term_tree.selection()
        domain_selection = self.lexicon_domain_tree.selection()
        if not selection or not domain_selection:
            return
        code = domain_selection[0]
        term = self.lexicon_term_tree.item(selection[0], "values")[0]
        self.lexicon_data[code] = [item for item in self.lexicon_data.get(code, []) if item != term]
        if not self.lexicon_data[code]:
            self.lexicon_data.pop(code, None)
        self._save_lexicon()
        self._refresh_lexicon_view()

    def _remove_selected_lexicon_domain(self) -> None:
        selection = self.lexicon_domain_tree.selection()
        if not selection:
            return
        code = selection[0]
        self.lexicon_data.pop(code, None)
        self._save_lexicon()
        self._refresh_lexicon_view()

    def _show_lexicon_term_menu(self, event: tk.Event) -> None:
        row_id = self.lexicon_term_tree.identify_row(event.y)
        if row_id:
            self.lexicon_term_tree.selection_set(row_id)
        selection = self.lexicon_term_tree.selection()
        if not selection:
            return
        values = self.lexicon_term_tree.item(selection[0], "values")
        if not values:
            return
        self.keyword_var.set(str(values[0]))
        self._sync_target_display()
        menu = tk.Menu(self.lexicon_term_tree, tearoff=0)
        menu.add_command(label=self._t("view_kwic"), command=lambda: self._switch_view("kwic"))
        menu.add_command(label=self._t("move_to_domain"), command=lambda: self._move_term_dialog(self.keyword_var.get().strip(), self.lexicon_domain_var.get().strip()))
        menu.add_command(label=self._t("remove_term"), command=self._remove_selected_lexicon_term)
        menu.tk_popup(event.x_root, event.y_root)

    def _resolve_to_lemma(self, term: str) -> str:
        candidate = term.strip()
        if not candidate:
            return ""
        if not self.last_result:
            return candidate
        tokens = self.last_result.get("tokens", [])
        direct_hits = [str(item.get("lemma", "")).strip() for item in tokens if str(item.get("lemma", "")).strip() == candidate]
        if direct_hits:
            return candidate
        mapped = [str(item.get("lemma", "")).strip() for item in tokens if str(item.get("surface", "")).strip() == candidate]
        mapped = [item for item in mapped if item]
        if not mapped:
            return candidate
        return Counter(mapped).most_common(1)[0][0]

    def _bulk_add_lemmas(self, lemma_domain_pairs: list[tuple[str, str]]) -> int:
        """lemma_domain_pairs: (lemma, domain_code) in that order."""
        lexicon = self._load_lexicon_data()
        added = 0
        for lemma, domain in lemma_domain_pairs:
            normalized_lemma = self._resolve_to_lemma(lemma)
            normalized_domain = (domain or self.selected_domain_var.get().strip() or "Z99").strip()
            if not normalized_lemma:
                continue
            lexicon.setdefault(normalized_domain, [])
            if normalized_lemma not in lexicon[normalized_domain]:
                lexicon[normalized_domain].append(normalized_lemma)
                added += 1
        write_json(lexicon, Path(self.lexicon_var.get().strip()))
        self.lexicon_data = lexicon
        return added

    def _lexicon_add_term(self, term: str, domain: str) -> None:
        lemma = self._resolve_to_lemma(term)
        code = domain.strip() or self.selected_domain_var.get().strip() or "Z99"
        if not lemma:
            return
        try:
            self._bulk_add_lemmas([(lemma, code)])
            self.status_var.set(f"{lemma} -> {code}")
        except Exception as exc:
            messagebox.showerror(tr(self.current_language, "analysis_failed"), str(exc))

    def _move_term_dialog(self, term: str, current_domain: str) -> None:
        lemma = self._resolve_to_lemma(term)
        if not lemma:
            return
        target = simpledialog.askstring(
            self._t("move_to_domain"),
            self._t("select_domain_prompt"),
            initialvalue=current_domain or "A1",
            parent=self.root,
        )
        if not target:
            return
        target_code = target.strip()
        lexicon = self._load_lexicon_data()
        for code, words in list(lexicon.items()):
            if isinstance(words, list):
                lexicon[code] = [word for word in words if word != lemma]
                if not lexicon[code]:
                    lexicon.pop(code, None)
        lexicon.setdefault(target_code, [])
        if lemma not in lexicon[target_code]:
            lexicon[target_code].append(lemma)
        write_json(lexicon, Path(self.lexicon_var.get().strip()))
        self.lexicon_data = lexicon
        self.selected_domain_var.set(target_code)
        self._sync_target_display()
        self._refresh_lexicon_view()

    def _open_semantic_tagger_popup(self) -> None:
        if not self.last_result:
            messagebox.showinfo(tr(self.current_language, "analysis_failed"), tr(self.current_language, "no_analysis"))
            return
        popup = tk.Toplevel(self.root)
        popup.title(self._t("semantic_tagger"))
        popup.geometry("980x720")
        popup.transient(self.root)
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(1, weight=1)

        top = ttk.Frame(popup, style="App.TFrame", padding=12)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text=self._t("semantic_tagger"), style="Header.TLabel").pack(side="left")
        ttk.Label(top, text=self._t("lemma_note"), style="Subtle.TLabel").pack(side="left", padx=(12, 0))

        body = ttk.Frame(popup, style="App.TFrame", padding=(12, 0, 12, 12))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        table = ttk.Treeview(body, columns=("surface", "lemma", "freq", "current", "target"), show="headings")
        table.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(body, orient="vertical", command=table.yview).grid(row=0, column=1, sticky="ns")
        self._set_table_headings(
            table,
            {
                "surface": tr(self.current_language, "surface"),
                "lemma": tr(self.current_language, "lemma"),
                "freq": tr(self.current_language, "count"),
                "current": tr(self.current_language, "domain_code"),
                "target": self._t("target_domain"),
            },
        )
        table.column("surface", width=180, anchor="w")
        table.column("lemma", width=200, anchor="w")
        table.column("freq", width=90, anchor="center")
        table.column("current", width=120, anchor="center")
        table.column("target", width=120, anchor="center")

        lemma_rows: dict[str, dict] = {}
        domain_counter_by_lemma: dict[str, Counter] = defaultdict(Counter)
        for token in self.last_result.get("tokens", []):
            lemma = str(token.get("lemma", "")).strip()
            surface = str(token.get("surface", "")).strip() or lemma
            domain_code = str(token.get("domain_code", "")).strip() or "Z99"
            if not lemma:
                continue
            bucket = lemma_rows.setdefault(lemma, {"surface": surface, "lemma": lemma, "freq": 0})
            bucket["freq"] += 1
            if len(surface) < len(str(bucket["surface"])):
                bucket["surface"] = surface
            domain_counter_by_lemma[lemma][domain_code] += 1

        for lemma, payload in sorted(lemma_rows.items(), key=lambda item: (-int(item[1]["freq"]), item[0])):
            current_domain = domain_counter_by_lemma[lemma].most_common(1)[0][0]
            table.insert("", tk.END, values=(payload["surface"], lemma, payload["freq"], current_domain, current_domain))

        action_bar = ttk.Frame(body, style="App.TFrame")
        action_bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        target_var = tk.StringVar(value=self.selected_domain_var.get().strip() or "A1")
        ttk.Label(action_bar, text=self._t("target_domain")).pack(side="left")
        ttk.Combobox(action_bar, textvariable=target_var, values=sorted(self.categories.keys()), width=14).pack(side="left", padx=(8, 10))

        def set_selected_domain() -> None:
            selection = table.selection()
            if not selection:
                return
            target = target_var.get().strip()
            if not target:
                return
            for row_id in selection:
                values = list(table.item(row_id, "values"))
                values[4] = target
                table.item(row_id, values=tuple(values))

        def import_rows(selected_only: bool) -> None:
            row_ids = list(table.selection()) if selected_only else list(table.get_children())
            pairs: list[tuple[str, str]] = []
            for row_id in row_ids:
                values = table.item(row_id, "values")
                if values:
                    pairs.append((str(values[1]), str(values[4])))
            added = self._bulk_add_lemmas(pairs)
            self._refresh_lexicon_view()
            self.status_var.set(f"{self._t('semantic_tagger')}: +{added}")

        ttk.Button(action_bar, text=self._t("set_selected_domain"), style="Ghost.TButton", command=set_selected_domain).pack(side="left")
        ttk.Button(action_bar, text=self._t("import_selected_lemma"), style="Primary.TButton", command=lambda: import_rows(True)).pack(side="left", padx=(8, 0))
        ttk.Button(action_bar, text=self._t("import_all_lemma"), style="Ghost.TButton", command=lambda: import_rows(False)).pack(side="left", padx=(8, 0))

    def _open_about_popup(self) -> None:
        messagebox.showinfo(self._t("about"), self._t("about_text"))

    def _save_project(self) -> None:
        output = filedialog.asksaveasfilename(
            title=tr(self.current_language, "save_project"),
            defaultextension=".wmja.json",
            filetypes=[("Bunseki Project", "*.wmja.json"), ("JSON Files", "*.json")],
        )
        if not output:
            return
        payload = {
            "settings": {
                "language": self.current_language,
                "mode": self.mode_var.get(),
                "lexicon_path": self.lexicon_var.get(),
                "min_freq": self.min_freq_var.get(),
                "top_n": self.top_n_var.get(),
                "unknown_domain": self.unknown_domain_var.get(),
                "keyword": self.keyword_var.get(),
                "selected_domain": self.selected_domain_var.get(),
                "view": self.current_view_var.get(),
            },
            "texts": {"primary": self.primary_text.get("1.0", tk.END).strip()},
            "results": {"primary": self.last_result, "left": self.left_result, "right": self.right_result},
        }
        path = Path(output)
        save_project_file(path, payload)
        self.current_project_path = path
        self.recent_files["recent_project_files"] = push_recent_file(self.recent_files.get("recent_project_files", []), str(path))
        self._save_recent_files()
        self.status_var.set(f"{tr(self.current_language, 'save_project')}: {path.name}")

    def _open_project(self) -> None:
        selected = filedialog.askopenfilename(
            title=tr(self.current_language, "open_project"),
            filetypes=[("Bunseki Project", "*.wmja.json"), ("JSON Files", "*.json")],
            initialdir=str(self.base_dir),
        )
        if not selected:
            return
        payload = open_project_file(Path(selected))
        settings = payload.get("settings", {})
        texts = payload.get("texts", {})
        results = payload.get("results", {})

        self.language_var.set(settings.get("language", "zh"))
        self.mode_var.set(settings.get("mode", "C"))
        self.lexicon_var.set(settings.get("lexicon_path", str(self.default_lexicon)))
        self.min_freq_var.set(settings.get("min_freq", "1"))
        self.top_n_var.set(settings.get("top_n", ""))
        self.unknown_domain_var.set(settings.get("unknown_domain", "Z99"))
        self.keyword_var.set(settings.get("keyword", ""))
        self.selected_domain_var.set(settings.get("selected_domain", ""))
        self.primary_text.delete("1.0", tk.END)
        self.primary_text.insert("1.0", texts.get("primary", ""))
        self.last_result = results.get("primary")
        self.left_result = results.get("left")
        self.right_result = results.get("right")
        self._apply_language()
        if self.last_result:
            self._render_analysis_result(self.last_result)
            self._refresh_profile_view()
            self._refresh_kwic_view()
        self._switch_view(settings.get("view", "workspace"))
        self.current_project_path = Path(selected)
        self.recent_files["recent_project_files"] = push_recent_file(self.recent_files.get("recent_project_files", []), selected)
        self._save_recent_files()
        self.status_var.set(f"{tr(self.current_language, 'open_project')}: {Path(selected).name}")

    def _export_json(self) -> None:
        if not self.last_result:
            messagebox.showinfo(tr(self.current_language, "analysis_failed"), tr(self.current_language, "no_analysis"))
            return
        output = filedialog.asksaveasfilename(
            title=tr(self.current_language, "export_json"),
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
        )
        if output:
            write_json(self.last_result, Path(output))
            self.status_var.set(f"{tr(self.current_language, 'export_json')}: {Path(output).name}")

    def _export_csv(self) -> None:
        if not self.last_result:
            messagebox.showinfo(tr(self.current_language, "analysis_failed"), tr(self.current_language, "no_analysis"))
            return
        output = filedialog.asksaveasfilename(
            title=tr(self.current_language, "export_csv"),
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if output:
            write_csv(self.last_result, Path(output))
            self.status_var.set(f"{tr(self.current_language, 'export_csv')}: {Path(output).name}")

    def _export_bundle(self) -> None:
        if not self.last_result:
            messagebox.showinfo(tr(self.current_language, "analysis_failed"), tr(self.current_language, "no_analysis"))
            return
        output_dir = filedialog.askdirectory(title=tr(self.current_language, "export_bundle"))
        if output_dir:
            write_csv_bundle(self.last_result, Path(output_dir))
            self.status_var.set(f"{tr(self.current_language, 'export_bundle')}: {Path(output_dir).name}")

    def _clear_primary(self) -> None:
        self.primary_text.delete("1.0", tk.END)
        self.summary_text.delete("1.0", tk.END)
        self.json_output.delete("1.0", tk.END)
        self.compare_left_text.delete("1.0", tk.END)
        self.compare_right_text.delete("1.0", tk.END)
        for table in (
            self.tokens_table,
            self.lemma_table,
            self.domain_table,
            self.profile_domain_tree,
            self.profile_word_tree,
            self.kwic_tree,
            self.compare_lemma_table,
            self.compare_domain_table,
        ):
            self._fill_table(table, [])
        self.last_result = None
        self.left_result = None
        self.right_result = None
        self.keyword_var.set("")
        self.selected_domain_var.set("")
        self._refresh_status_ready()

    @staticmethod
    def _fill_table(tree: ttk.Treeview, rows: list[tuple]) -> None:
        for item_id in tree.get_children():
            tree.delete(item_id)
        for row in rows:
            tree.insert("", tk.END, values=row)

    def _highlight_text_widget(self, widget: tk.Text, keyword: str) -> None:
        widget.tag_remove("highlight", "1.0", tk.END)
        if not keyword:
            return
        start = "1.0"
        while True:
            start = widget.search(keyword, start, stopindex=tk.END)
            if not start:
                break
            end = f"{start}+{len(keyword)}c"
            widget.tag_add("highlight", start, end)
            start = end

    def _save_recent_files(self) -> None:
        write_recent_files(self.recent_path, self.recent_files)


def launch_gui() -> None:
    root = tk.Tk()
    WmatrixJAApp(root)
    root.mainloop()
