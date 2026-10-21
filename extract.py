#!/usr/bin/env python3
"""Read a folder of daily journal notes (and optionally a calendar dump) and emit data.json.

Design rules that must not drift:

1. Only acts go in. An act is something you did and could have chosen not to do.
   Outcomes (weight, client count, views) belong in the evidence layer, never in a wedge.
2. Plans are not acts. A journal template that writes a workout plan into every day
   would make it look like you trained daily. The truth is the record line.
   Same idea everywhere else: unchecked todos are not evidence.
3. Acts and notes are different things. An act is dated and was done: a calendar
   entry, a workout record, a checked todo. A reflection ("let me embrace the
   feeling") is a note. Notes are evidence you read inside a wedge; they never change
   how full it looks. Mixing them inflates whatever you happened to write about that week.
4. Anything the rules cannot place goes to `unsorted` and is shown in the UI.
   A silent drop would quietly lie about how full a wedge is.
"""
import argparse, datetime as dt, json, os, re, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_config(name):
    """config/<name>.local.json wins over config/<name>.json.

    The committed files are a working example that reads sample/journal. Your own
    paths, names and patterns go in the .local.json files, which git ignores.
    """
    local = HERE / "config" / (name + ".local.json")
    path = local if local.exists() else HERE / "config" / (name + ".json")
    return json.loads(path.read_text(encoding="utf-8"))


def load_settings():
    # Settings merge key by key, so a local file only needs what differs.
    s = json.loads((HERE / "config/settings.json").read_text(encoding="utf-8"))
    local = HERE / "config/settings.local.json"
    if local.exists():
        s.update(json.loads(local.read_text(encoding="utf-8")))
    return s


def resolve(p):
    p = Path(os.path.expanduser(p))
    return p if p.is_absolute() else HERE / p


S = load_settings()
JOURNALS = [resolve(p) for p in S["journal_dirs"]]
VAULT_ROOT = resolve(S["vault_root"]) if S.get("vault_root") else None
EK = resolve(S["calendar_json"]) if S.get("calendar_json") else None
SEC = S["sections"]

# Self-judgment markers. Counted, never coloured. The point is to see whether this
# tracks the cycle, not to score the day.
JUDGMENT = re.compile(S["self_judgment"], re.I)
KIND_LETTER = re.compile(S["kind_letter"], re.I)


def nfc(s):
    return unicodedata.normalize("NFC", s)


def strip_md(s):
    s = re.sub(r"!?\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`>]+", "", s)
    s = re.sub(r"https?://\S+", "", s)
    return re.sub(r"\s+", " ", s).strip(" .·-\t")


def section(body, heading_pat):
    m = re.search(r"^##\s*\*{0,2}" + heading_pat + r"[^\n]*\n(.*?)(?=^##\s|\Z)", body, re.S | re.M)
    return m.group(1) if m else ""


def bullets(sec):
    """Top-level bullets with their indented children, in order."""
    out, cur = [], None
    for line in sec.splitlines():
        m = re.match(r"^-\s+(.*)$", line)
        if m:
            cur = {"text": strip_md(m.group(1)), "children": []}
            out.append(cur)
            continue
        m = re.match(r"^(?:\t+|\s{2,})-\s*(.*)$", line)
        if m and cur is not None:
            t = strip_md(m.group(1))
            if t:
                cur["children"].append(t)
    return out


class Rules(object):
    def __init__(self, taxonomy, people):
        self.wedges = taxonomy["wedges"]
        self.rules = [(r["wedge"], re.compile(r["pattern"], re.I)) for r in taxonomy["rules"]]
        self.contexts = [(c["id"], re.compile(c["pattern"], re.I)) for c in taxonomy["contexts"]]
        self.drop = re.compile(taxonomy["drop"]["pattern"], re.I)
        self.admin = re.compile(taxonomy["admin"]["pattern"], re.I)
        self.close = self._roster(people.get("close"))
        self.clients = self._roster(people.get("clients"))
        self.mentors = self._roster(people.get("mentors"))

    @staticmethod
    def _roster(names):
        return re.compile("|".join(re.escape(n) for n in names), re.I) if names else None

    def wedge_of(self, text):
        score = {}
        for wid, pat in self.rules:
            n = len(pat.findall(text))
            if n:
                score[wid] = score.get(wid, 0) + n
        # Rosters beat keywords. A named person settles what an act was better than
        # any word in it: dinner with a close friend is not networking, and a session with a
        # client is reaching out even though it looks like a meeting.
        if self.mentors and self.mentors.search(text):
            score["absorb"] = score.get("absorb", 0) + 3
            score.pop("reach", None)
        elif self.clients and self.clients.search(text):
            score["reach"] = score.get("reach", 0) + 3
        elif self.close and self.close.search(text):
            score["tend"] = score.get("tend", 0) + 2
            score.pop("reach", None)
        if not score:
            return "admin" if self.admin.search(text) else None
        return max(score.items(), key=lambda kv: kv[1])[0]

    def context_of(self, text, default="personal"):
        for cid, pat in self.contexts:
            if pat.search(text):
                return cid
        return default


def subsection(sec, name):
    m = re.search(r"^\*" + name + r"\*[^\n]*\n(.*?)(?=^\*\S|\Z)", sec, re.S | re.M)
    return m.group(1) if m else ""


def journal_files():
    """Every note whose name starts with a date, in every journal folder.

    Folders are read recursively because old entries often get moved into an
    archive. The date prefix keeps other notes in those folders out.
    """
    out = []
    for j in JOURNALS:
        for p in j.rglob("*.md"):
            m = re.match(r"(\d{4}-\d{2}-\d{2})", nfc(p.name))
            if m:
                out.append((p, m.group(1)))
    return sorted(out, key=lambda x: nfc(x[0].name))


def journal_days(rules, date_from, date_to):
    days = {}
    for p, date in journal_files():
        if not (date_from <= date <= date_to):
            continue
        body = p.read_text(encoding="utf-8", errors="replace")
        acts, notes, unsorted_, texts = [], [], [], []
        # Relative to the vault root when one is set, so a link can open the note.
        rel = nfc(str(p.relative_to(VAULT_ROOT))) if VAULT_ROOT and VAULT_ROOT in p.parents else nfc(p.name)

        def add(text, source, kind="act", force=None):
            if not text or len(text) < 2:
                return
            texts.append(text)
            item = {"date": date, "text": text, "source": source, "kind": kind,
                    "context": rules.context_of(text), "note": rel}
            w = force or rules.wedge_of(text)
            if kind == "note":
                item["wedge"] = w
                notes.append(item)
            elif w:
                item["wedge"] = w
                acts.append(item)
            else:
                unsorted_.append(item)

        # Workout. A record line (`- Done: ...`) is a workout by definition, so it is
        # forced to `move` even when it names an exercise no rule knows yet. A plan line
        # (one a template writes in every day) is never read, or every day would look
        # like a training day.
        ex = section(body, SEC["workout"])
        done = []
        labels = "|".join(S["workout_record_labels"])
        mm = re.search(r"^[ \t]*-[ \t]*(?:" + labels + r")[ \t]*:[ \t]*(.*(?:\n(?![ \t]*(?:[-*>#]|$)).*)*)", ex, re.M)
        if mm and strip_md(mm.group(1)) and not re.match(S["workout_rest"], strip_md(mm.group(1)), re.I):
            done.append(strip_md(mm.group(1)))
        # Optional table with a record column, one row per exercise.
        rows = [r for r in ex.splitlines() if r.lstrip().startswith("|")]
        col_name = S.get("workout_table_column")
        if rows and col_name:
            head = [c.strip() for c in rows[0].strip().strip("|").split("|")]
            if col_name in head:
                col = head.index(col_name)
                for r in rows[2:]:
                    cells = [c.strip() for c in r.strip().strip("|").split("|")]
                    cell = strip_md(cells[col]) if col < len(cells) else ""
                    if cell and not re.match(S["workout_table_skip"], cell, re.I):
                        done.append("%s %s" % (cells[1] if len(cells) > 1 else "", cell))
        if done:
            # Prefixed because a memo is often one letter (U, L) and add() drops those.
            add("workout: " + " · ".join(done), "workout", force="move")
        # Checked boxes under a named sub-heading carry their own flow, for example
        # mobility work is `move` and an evening stretch is `still`.
        for name, wedge in S["workout_checklists"]:
            for mark, t in re.findall(r"^\s*-\s*\[([ xX])\]\s*(.+)$", subsection(ex, name), re.M):
                if mark.lower() == "x":
                    add(strip_md(t), "workout", force=wedge)

        # Intentions: reflections. Read as evidence, never counted as acts.
        kind_letter = False
        for b in bullets(section(body, SEC["reflections"])):
            if KIND_LETTER.search(b["text"]):
                kind_letter = bool(b["children"])
            for c in b["children"]:
                add(c, "journal", kind="note")

        for t in re.findall(r"^\s*-\s*\[[xX]\]\s*(.+)$", section(body, SEC["todos"]), re.M):
            add(re.sub(S["todo_suffix"], "", strip_md(t)), "todo")

        # Quick captures (dictated notes, pins). Read as notes, like reflections.
        for line in section(body, SEC["captures"]).splitlines():
            t = strip_md(re.sub(r"^\s*-\s*", "", line))
            t = re.sub(r"^\d{1,2}:\d{2}\s*", "", t)
            if t:
                add(t, "pinboard", kind="note")

        blob = "\n".join(texts) + "\n" + body
        days[date] = {
            "acts": acts,
            "notes": notes,
            "unsorted": unsorted_,
            "selfKindness": kind_letter,
            "selfJudgment": bool(JUDGMENT.search(blob)),
            "title": strip_md(nfc(p.stem)[11:]),
            "file": rel,
        }
    return days


def calendar_acts(rules, date_from, date_to):
    if not EK or not EK.exists():
        return [], []
    ek = json.loads(EK.read_text(encoding="utf-8"))
    byid = {c["id"]: c for c in ek["calendars"]}
    acts, unsorted_, seen = [], [], set()
    for e in ek["events"]:
        if not (date_from <= e["date"] <= date_to):
            continue
        title = strip_md(e["title"])
        if not title or rules.drop.search(title):
            continue
        cal = byid.get(e["cal"], {})
        # Public holidays are often subscribed on several calendars, and the same lunch
        # can sit on two accounts. Dedupe on (date, time, normalised title).
        k = (e["date"], e.get("time"), re.sub(r"[^0-9a-z가-힣]", "", title.lower())[:34])
        if k in seen:
            continue
        seen.add(k)
        # A whole calendar can stand for a context (a work account, a practice calendar).
        ctx = next((c["context"] for c in S.get("calendar_contexts", [])
                    if all(cal.get(k) == v for k, v in c.items() if k != "context")), None)
        ctx = ctx or rules.context_of(title)
        item = {"date": e["date"], "text": title, "source": "calendar", "kind": "act",
                "context": ctx, "time": e.get("time")}
        w = rules.wedge_of(title)
        # A dated meeting with a person is an act even when no keyword fires:
        # a personal calendar entry naming someone is reaching or tending.
        if not w and re.search(r"\bx\b|,|/|와|과|랑|님|씨|with |at ", title) and len(title) < 60:
            w = "tend" if (rules.close and rules.close.search(title)) else "reach"
        if w:
            item["wedge"] = w
            acts.append(item)
        else:
            unsorted_.append(item)
    return acts, unsorted_


def blank():
    return {"acts": [], "notes": [], "unsorted": [], "selfKindness": False,
            "selfJudgment": False, "title": "", "file": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="date_from", default=None)
    ap.add_argument("--to", dest="date_to", default=None)
    ap.add_argument("--out", default=str(HERE / "data.json"))
    a = ap.parse_args()

    today = dt.date.today().isoformat()
    # Without --to, end at the latest entry, so an old or sample journal still shows.
    dates = [d for _, d in journal_files() if d <= today]
    date_to = a.date_to or (max(dates) if dates else today)
    date_from = a.date_from or (dt.date.fromisoformat(date_to) - dt.timedelta(days=89)).isoformat()

    taxonomy = load_config("taxonomy")
    people = load_config("people")
    rules = Rules(taxonomy, people)

    days = journal_days(rules, date_from, date_to)
    cal_acts, cal_unsorted = calendar_acts(rules, date_from, date_to)
    for it in cal_acts:
        days.setdefault(it["date"], blank())["acts"].append(it)
    for it in cal_unsorted:
        days.setdefault(it["date"], blank())["unsorted"].append(it)

    covered = sorted(days)
    data = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "range": {"from": covered[0] if covered else date_from,
                  "to": covered[-1] if covered else date_to},
        "vault": S.get("obsidian_vault") or "",
        "wedges": taxonomy["wedges"],
        "days": days,
    }
    Path(a.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    n_acts = sum(len(d["acts"]) for d in days.values())
    n_notes = sum(len(d["notes"]) for d in days.values())
    n_uns = sum(len(d["unsorted"]) for d in days.values())
    per = {}
    for d in days.values():
        for it in d["acts"]:
            per[it["wedge"]] = per.get(it["wedge"], 0) + 1
    print("%s .. %s  days %d  acts %d  notes %d  unsorted %d"
          % (data["range"]["from"], data["range"]["to"], len(days), n_acts, n_notes, n_uns))
    print("  " + "  ".join("%s %d" % (w["id"], per.get(w["id"], 0)) for w in taxonomy["wedges"]))


if __name__ == "__main__":
    main()
