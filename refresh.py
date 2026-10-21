#!/usr/bin/env python3
"""extract -> render -> write the wheel page (settings "output").

Same shape as the Layers prototype: a script computes data.json, a template swallows
it at __DATA__. Keeping them apart is what let Layers be rebuilt after the scratchpad
was wiped, so do not inline the data into the template by hand.
"""
import argparse, json, subprocess, sys
from pathlib import Path

from extract import HERE, S, resolve

OUT = resolve(S["output"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-extract", action="store_true")
    a = ap.parse_args()

    if not a.no_extract:
        cmd = [sys.executable, str(HERE / "extract.py")]
        if a.date_from: cmd += ["--from", a.date_from]
        if a.date_to: cmd += ["--to", a.date_to]
        subprocess.run(cmd, check=True)

    data = (HERE / "data.json").read_text(encoding="utf-8")
    page = (HERE / "template.html").read_text(encoding="utf-8").replace("__DATA__", data)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print("wrote %s (%.0f KB)" % (out, len(page) / 1024))


if __name__ == "__main__":
    main()
