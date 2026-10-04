# Karens-Class

A 15-session upper-division sociology seminar built on **A Different World** — the 2026 Netflix
revival *and* the 1987–1993 original it keeps calling back to.

> **The through-line:** every session pairs a 2026 episode with the original episode(s) it "calls
> back" to, and asks what changed and what did not. The show's own device — the callback — is the
> course's method. Black experience is not a specialty bolted onto "general" sociology; it is where
> the general theory gets tested.

**Live course site:** https://joenobody-ai.github.io/Karens-Class/
**Reference site the homework points at:** https://joenobody-ai.github.io/different-world-notes/v2/

---

## What's in here

| Path | What it is |
|---|---|
| `course/syllabus.md` | The syllabus: description, outcomes, schedule, assessment, policies |
| `course/class-01.md` … `class-15.md` | The 15 sessions: viewing, concepts, 75-minute lecture arc, discussion questions, **instructor notes**, key terms, further reading |
| `course/assignments/homework-01.md` … `homework-15.md` | One assignment per session, with prompt, sources, and grading criteria |
| `course/exams/midterm.md`, `final.md` | The two exams, as issued to students |
| `course/exams/midterm-key.md`, `final-key.md` | Model answers, point allocations, and the grading rubric — **instructor material** |
| `course/instructor-guide.md` | How to run the room: norm-setting, the hard conversations, objections and answers, accessibility, adaptation notes |
| `course/sources.md` | Bibliography — books and articles by citation, plus institution links that were HTTP-checked on the build date |
| `course/rubrics.md` | Reusable rubrics (discussion, writing, data exercise, capstone) |
| `docs/` | Generated HTML for the course site — this is what GitHub Pages serves |
| `scripts/` | The build and the verifiers |

## The two-layer approach to evidence

The course distinguishes, everywhere, between three kinds of claim:

1. **Documented** — an episode title, air date, director, writer, cast credit, or published summary.
   Checkable against the reference site, which cites its sources.
2. **Interpretation** — a reading of what a scene or a season argues. Labelled as a reading.
3. **Instructor hypothesis** — a claim offered for the room to test.

Students are graded on keeping those apart. Homework 1 makes them do it explicitly, and it recurs.

Statistics in the materials are deliberately written as **"check this before you teach it"** items:
every figure carries a source and a capture date, because numbers about health, wealth and education
move faster than a syllabus. Homework 5 and 14 build the re-check into the assignment.

## Rebuilding

```bash
. .venv/bin/activate                      # needs: uv pip install markdown  (see scripts/requirements.txt)
python3 scripts/build_course.py           # markdown -> docs/
python3 scripts/verify_course.py          # must print ALL CHECKS PASS
```

`build_course.py` uses the `markdown` package from `.venv` (see `scripts/requirements.txt`).
`verify_course.py` is stdlib-only and checks: all 15 sessions and 15 homework files exist and are
consistent with `data/course_catalog.json`, every 2026 episode is taught in order, every original
episode assigned is real (title *and* air date matched against the episode list), every deep link into
the reference site points at an anchor that actually exists, every external link was HTTP-verified as
live or is listed in the documented blocked-to-bots allowlist, the lecture arc in every session sums to
75 minutes, and the built site is complete with no unrendered markdown.

## Instructor keys and this repo being public

`instructor/` holds the exam keys. It is **not linked from the course site's navigation** and carries
a do-not-distribute banner, but it does live in this repository. If you need it out of students'
reach: `python3 scripts/build_course.py --no-instructor` and delete the folder, or make the repo
private. That trade-off is yours, not the script's — so the script prints a warning when it writes them.

## Licence and attribution

Course materials: CC BY 4.0 — use them, adapt them, keep the attribution.
*A Different World* is the property of its rights holders; this course teaches *about* the show and
reproduces no scripts, stills, or episode footage. Episode facts (titles, air dates, credits) are
used for identification and commentary. See `course/sources.md` for the full note.
