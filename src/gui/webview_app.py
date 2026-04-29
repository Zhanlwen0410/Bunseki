from pathlib import Path

from src.gui.webview_api import WebviewAPI


def launch_webview() -> None:
    try:
        import webview
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "pywebview is required for the modern webview UI. Install dependencies with 'py -m pip install -r requirements.txt'."
        ) from exc

    base_dir = Path(__file__).resolve().parents[2]
    html_path = base_dir / "src" / "webui" / "index.html"
    api = WebviewAPI(base_dir)
    window = webview.create_window(
        "Bunseki",
        html_path.as_uri(),
        js_api=api,
        width=1480,
        height=940,
        min_size=(1180, 760),
    )
    webview.start(debug=False, http_server=True)
