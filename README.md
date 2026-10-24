# otter

A life dashboard that fills itself from the daily journal you already keep.

Point it at a folder of dated Markdown notes. It reads what you did each day, sorts
each act into one of six flows, and draws two pages:

- **the wheel** (`out/index.html`): the last 7, 14 or 30 days as one wheel, with the
  acts behind each wedge.
- **the path** (`out/path.html`): a longer stretch as a route that wanders between the
  flows day by day, with the questions you were asking along the way. It holds no
  journal text, so you can share it.

No Python, or no Markdown journal? [PROMPT.md](PROMPT.md) has a prompt that makes a
weekly otter page from any journal with Claude, in English and Korean. There is also a
[short guide](https://claude.ai/artifact/5Y4NfRYxxwtLZShJoAW43e). That version counts
what happened in your entries, keeps a list of your wants and questions, and marks
which ones came true.

Six flows in three facing pairs:

| pair | | |
|---|---|---|
| motion and rest | **Move** | **Still** |
| taking in and putting out | **Absorb** | **Create** |
| holding close and opening out | **Tend** | **Reach** |

An otter floats in the middle. She does not wilt when a wedge is empty.

## Try it in a minute

Python 3.8 or later, no packages to install.

```
git clone https://github.com/ebcreation-cloud/otter
cd otter
python3 refresh.py      # the wheel  -> out/index.html
python3 path.py         # the path   -> out/path.html
open out/path.html
```

This runs on `sample/journal`, eight weeks of notes for an invented person.

## Use your own journal

1. Copy `config/settings.json` to `config/settings.local.json` and change what
   differs. The local file is merged over the default key by key and is never
   committed, so your paths and names stay on your machine.
2. Run `python3 refresh.py` and look at the "no rule yet" list on the wheel page.
   Anything there is something otter could not place. Add words to
   `config/taxonomy.local.json` (start from a copy of `taxonomy.json`) until the list
   is short.
3. Copy `config/path.json` to `config/path.local.json` and write your own status,
   stretches and questions.

### What otter expects from a note

One note per day, its file name starting with the date: `2026-01-13.md` or
`2026-01-13 long run.md`. Notes can sit in subfolders; old entries moved into an
archive are still found. Inside, otter looks for four `##` sections. Their names are
settings, so use whatever headings your journal already has.

```markdown
## Reflections            <- sections.reflections: read, never counted
- Today
	- Felt calm most of the day.
- Letter to myself        <- kind_letter: was a kind note written?
	- You are doing more than you think.

## Workout                <- sections.workout
- Plan: upper body        <- ignored; plans are not acts
- Done: bench, rows       <- workout_record_labels: always counts as Move

*Stretch*                 <- workout_checklists: checked boxes under this label
- [x] Evening stretch        count as the flow you give them

## Todo                   <- sections.todos: checked boxes are acts
- [x] Coffee chat with a former colleague
- [ ] Read two chapters

## Captures               <- sections.captures: quick notes, read but not counted
- 08:12 idea: a map of how my weeks lean
```

A section that is missing is simply skipped. If your journal is free prose with no
checklists, the Todo section is the place to start: a checked line is the clearest
signal that something happened.

### Settings

| key | what it does |
|---|---|
| `journal_dirs` | folders to read, searched recursively. `~` works. |
| `vault_root`, `obsidian_vault` | set both to make acts on the wheel open their note in Obsidian. |
| `calendar_json` | optional calendar export (see below). |
| `calendar_contexts` | tag a whole calendar as a context, e.g. `{"source": "Exchange", "context": "work"}`. |
| `output`, `path_output` | where the two pages are written. |
| `sections` | your heading names for the four sections. |
| `workout_record_labels` | words before the colon on a workout record line. |
| `workout_rest` | a record that starts like this is a rest day, not a session. |
| `workout_table_column` | if you log workouts in a Markdown table, the column holding what was done. |
| `workout_checklists` | `[label, flow]` pairs for checkbox groups inside the workout section. |
| `todo_suffix` | text to strip from todo lines, such as a carry-over counter. |
| `self_judgment`, `kind_letter` | patterns counted side by side on the wheel page. |

`config/taxonomy.json` holds the matching rules: a regular expression per flow,
plus `admin` (errands that belong to no flow) and `drop` (calendar noise).
`config/people.json` holds rosters keyword matching cannot guess: who is close
(Tend), who is a client (Reach), who coaches or teaches you (Absorb). A name beats
a keyword, so dinner with a close friend is not counted as networking.

### Calendar (optional)

`calendar_json` points to a JSON file shaped like this:

```json
{"calendars": [{"id": "a1", "title": "Personal", "source": "iCloud"}],
 "events": [{"date": "2026-01-13", "time": "19:00", "title": "Dinner with Sam", "cal": "a1"}]}
```

Any exporter that writes this shape works. Calendar events are acts by definition,
since they were dated and attended.

## Why it is built this way

**Only acts go in the wheel.** An act is dated and was done: a calendar entry, a
workout record, a checked todo. Outcomes stay out: weight, client count, view count.
You cannot act on an outcome today, and a number you cannot move is not something to
look at every morning.

**Plans are not acts.** A journal template that writes a workout plan into every day
would make it look like you trained daily. Only the record line counts.

**Reflections are evidence, not volume.** A journal entry about coaching does not make
the Reach wedge bigger. It shows up inside the wedge when you open it.

**Nothing is scored.** Self-kindness and self-judgment are counted side by side and
drawn in the same weight of colour. A dashboard that grades you is a dashboard you
stop opening.

**Work is a tag, not a wedge.** A job feeds several flows at once: reading feeds
Absorb, shipping something feeds Create, new colleagues feed Reach. Splitting work
from life into separate wedges would cut a single day in half for no reason.

**The path is about questions.** Looking back over years of journals, the turning
points are rarely the days with big events. They are the days the question you were
asking yourself changed. So the path page puts the questions on the route.

**Failures to classify are shown.** Anything no rule places is listed on the page as
"no rule yet" instead of being dropped, so a wedge never looks fuller than it is.

The categories come from [self-determination theory](https://selfdeterminationtheory.org/)
(autonomy, competence, relatedness) and the self-kindness row from
[Neff's self-compassion work](https://self-compassion.org/). The pairing into opposites
is so that balance is visible as symmetry rather than as a target.

## Running it

```
python3 refresh.py                        # extract, then draw the wheel
python3 refresh.py --from 2026-01-01      # a specific window
python3 refresh.py --no-extract           # redraw only
python3 path.py                           # extract the path range, then draw the path
python3 path.py --from 2026-01-05 --to 2026-03-01
python3 sample/make_sample.py             # regenerate the sample journal
```

Without dates, otter reads the 90 days up to your latest note.

Interface strings live in `I18N` in `template.html` and `UI` in `path_template.html`.
Both pages have English and Korean.

## Privacy

`data.json` and `out/index.html` contain real journal lines and names. They are
gitignored, together with every `*.local.json`. The path page contains only daily
counts and the words you put in `path.local.json`, so read that file before you
share the page.

## License

MIT
