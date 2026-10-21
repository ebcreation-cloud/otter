#!/usr/bin/env python3
"""Draw otter's path: the route a stretch of days took across the six flows.

Reads data.json (runs extract.py first unless --no-extract), reduces each day to
counts per flow, and writes a single shareable HTML page. Day titles and journal
text are dropped on purpose, so the page can be shown to other people. The words on
the page (status, question, stretches, questions so far) come from config/path.json,
or config/path.local.json when it exists.
"""
import argparse, datetime as dt, html, json, subprocess, sys
from pathlib import Path

from extract import HERE, S, load_config, resolve

FLOWS = ("move", "still", "absorb", "create", "tend", "reach")
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}[hidden]{display:none!important}</style>
</head>
<body>
"""


def js(v):
    # Safe inside a <script> block even if a config string contains "</script>".
    return json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def series(data, date_from, date_to):
    """One entry per calendar day, empty days included, so gaps show as standing still."""
    out, d = [], dt.date.fromisoformat(date_from)
    while d.isoformat() <= date_to:
        day = data["days"].get(d.isoformat(), {})
        c = {}
        for act in day.get("acts", []):
            if act.get("wedge") in FLOWS:      # admin stays off the path, as it stays off the wheel
                c[act["wedge"]] = c.get(act["wedge"], 0) + 1
        out.append({"d": d.isoformat(), "c": c})
        d += dt.timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-extract", action="store_true")
    a = ap.parse_args()
    conf = load_config("path")
    date_from = a.date_from or conf.get("from")
    date_to = a.date_to or conf.get("to")

    if not a.no_extract:
        cmd = [sys.executable, str(HERE / "extract.py")]
        if date_from: cmd += ["--from", date_from]
        if date_to: cmd += ["--to", date_to]
        subprocess.run(cmd, check=True)

    data = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
    path = series(data, date_from or data["range"]["from"], date_to or data["range"]["to"])

    page = (HERE / "path_template.html").read_text(encoding="utf-8")
    page = (page.replace("__TITLE__", html.escape(conf.get("title", "otter's path")))
                .replace("__PATH__", js(path))
                .replace("__CONF__", js(conf)))
    out = Path(a.out) if a.out else resolve(S["path_output"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(HEAD + page + "</body>\n</html>\n", encoding="utf-8")
    print("wrote %s (%d days)" % (out, len(path)))


if __name__ == "__main__":
    main()
