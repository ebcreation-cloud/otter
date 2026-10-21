#!/usr/bin/env python3
"""Write eight weeks of made-up daily notes into sample/journal.

The person is invented. Three stretches: a settled routine, a trip home, and the
start of a side project. The notes use the default section names in
config/settings.json, so `python3 refresh.py` and `python3 path.py` work on a fresh
clone with no setup. Run again to regenerate; the seed keeps the output stable.
"""
import datetime as dt, random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "journal"
START = dt.date(2026, 1, 5)
DAYS = 56

ROUTINE = {
    "todo": ["Read two chapters of a novel", "Coffee chat with a former colleague", "Called Mum",
             "Listened to a podcast on sleep", "Booked the dentist", "Replied to the volunteer email",
             "Dinner together at home", "Online course, module 3", "Meetup on urban gardening"],
    "workout": ["Done: run 5k, easy", "Done: gym, squat and rows", "Done: pilates", "Done: swim 1km"],
}
TRIP = {
    "todo": ["Lunch together with Mum and Dad", "Called my sister", "Hike with Dad", "Family dinner, cooked for everyone",
             "Visited the old school", "Packing for the flight", "Walk alone by the river", "Read on the train"],
    "workout": ["Done: hike", "Done: long walk", "Record: rest day"],
}
PROJECT = {
    "todo": ["Wrote a blog draft", "Built the first page of the app", "Sketch for the logo", "Coffee chat about the project",
             "Emailed two people for feedback", "Read a book on design", "Committed the data parser", "Posted the first essay",
             "Paperwork for the tax return", "Yoga at home"],
    "workout": ["Done: gym, push day", "Done: run 8k", "Done: pilates", "Done: climbing"],
}
REFLECT = ["Felt calm most of the day.", "I keep wanting to start before I feel ready.", "Tired, but a good tired.",
           "Noticed I was comparing again.", "Small things went well today.", "I should have rested more, but it is fine."]
# Day index -> title in the file name. 0 is a Monday.
TITLES = {0: "first week back", 8: "book club", 13: "long run", 21: "flight home", 22: "Mum's kitchen",
          25: "old friends", 28: "hike", 32: "flying back", 33: "first draft", 37: "feedback",
          40: "shipped it", 48: "sunday reset"}
QUESTIONS = {7: "What would a slower week look like?", 24: "What do I miss when I am away?",
             41: "Am I making this for me, or for an audience?"}


def note(i, rnd):
    date = START + dt.timedelta(days=i)
    stretch = ROUTINE if i < 21 else TRIP if i < 33 else PROJECT
    title = TITLES.get(i, "")
    done = rnd.sample(stretch["todo"], k=rnd.randint(1, 3))
    left = [t for t in stretch["todo"] if t not in done][:1]
    lines = ["# " + date.strftime("%A %d %B"), "", "## Reflections", "- Today", "\t- " + rnd.choice(REFLECT)]
    if i in QUESTIONS:
        lines += ["- Question", "\t- " + QUESTIONS[i]]
    if rnd.random() < .3:
        lines += ["- Letter to myself", "\t- You are doing more than you think."]
    lines += ["", "## Workout", "- Plan: whatever feels right"]
    if rnd.random() < .7:
        lines.append("- " + rnd.choice(stretch["workout"]))
    lines += ["", "*Stretch*", "- [%s] Evening stretch" % ("x" if rnd.random() < .4 else " "), "",
              "## Todo"] + ["- [x] " + t for t in done] + ["- [ ] " + t for t in left]
    lines += ["", "## Captures"]
    if rnd.random() < .4:
        lines.append("- %02d:%02d idea: a map of how my weeks lean" % (rnd.randint(7, 22), rnd.randint(0, 59)))
    name = date.isoformat() + (" " + title if title else "") + ".md"
    return name, "\n".join(lines) + "\n"


def main():
    rnd = random.Random(42)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.md"):
        old.unlink()
    for i in range(DAYS):
        if rnd.random() < .12:      # some days have no note at all
            continue
        name, text = note(i, rnd)
        (OUT / name).write_text(text, encoding="utf-8")
    print("wrote %d notes to %s" % (len(list(OUT.glob("*.md"))), OUT))


if __name__ == "__main__":
    main()
