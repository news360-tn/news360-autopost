"""owner 26 Nov: builds dashboard/worker.js (the Cloudflare Worker) from worker_template.js + Index.html.  python dashboard/build_worker.py"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build():
    html = (HERE / "Index.html").read_text(encoding="utf-8")
    tpl = (HERE / "worker_template.js").read_text(encoding="utf-8")
    js = tpl.replace("__HTML__", json.dumps(html, ensure_ascii=False).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    (HERE / "worker.js").write_text(js, encoding="utf-8")
    # owner 26 Nov: Cloudflare Pages (news360-backend.pages.dev) - the same file as _worker.js, plus a zip to upload in one go
    import zipfile
    pages = HERE / "pages"
    pages.mkdir(exist_ok=True)
    (pages / "_worker.js").write_text(js, encoding="utf-8")
    with zipfile.ZipFile(pages / "news360-backend.zip", "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo("_worker.js", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, js)
    return len(js)


if __name__ == "__main__":
    print("worker.js:", build(), "bytes")
