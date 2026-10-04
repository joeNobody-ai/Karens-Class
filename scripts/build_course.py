#!/usr/bin/env python3
"""build_course.py — render the course markdown into a small static site.

Design goals: readable, printable, no external requests, works without JavaScript, and honest about
what it is. Instructor material (exam keys) is rendered into site/instructor/ with a do-not-distribute
banner and is deliberately NOT linked from the student navigation.

Usage:
    python3 scripts/build_course.py                  # build everything
    python3 scripts/build_course.py --no-instructor  # omit exam keys from the built site
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
COURSE = ROOT / "course"
ASSETS = ROOT / "assets"
CATALOG = json.loads((ROOT / "data/course_catalog.json").read_text())

try:
    import markdown  # type: ignore
except ImportError:                                            # pragma: no cover
    print("ERROR: the 'markdown' package is required. Create the venv first:\n"
          "  uv venv .venv && . .venv/bin/activate && uv pip install markdown", file=sys.stderr)
    raise SystemExit(2)

MD = markdown.Markdown(extensions=["tables", "attr_list", "sane_lists", "md_in_html"],
                       extension_configs={"tables": {"use_align_attribute": False}})

CSS = """/* SOC 4150 course site — no external fonts, no scripts required */
:root{
 --paper:#fbfaf7; --panel:#f4f1ea; --ink:#1b1a18; --soft:#4a463f; --mute:#7c766c;
 --line:#ded8cd; --navy:#152743; --gold:#9a7526; --red:#8c2f1c; --ok:#2c6046;
 --serif:ui-serif,"Iowan Old Style",Palatino,Georgia,serif;
 --sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
 --measure:72ch;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:4.5rem}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.62 var(--sans)}
a{color:var(--navy);text-underline-offset:2px}
a:hover{color:var(--red)}
header.top{position:sticky;top:0;z-index:10;background:rgba(251,250,247,.93);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
header.top .in{max-width:1180px;margin:0 auto;padding:.7rem 1.2rem;display:flex;gap:1rem;align-items:center;flex-wrap:wrap}
.brand{font:600 1.02rem/1.2 var(--serif);text-decoration:none;color:var(--ink)}
.brand em{color:var(--gold);font-style:normal}
header.top nav{margin-left:auto;display:flex;gap:.1rem;flex-wrap:wrap}
header.top nav a{font-size:.83rem;padding:.36rem .58rem;border-radius:999px;text-decoration:none;color:var(--soft)}
header.top nav a:hover{background:var(--panel);color:var(--ink)}
header.top nav a.here{background:var(--navy);color:#fff}
main{max-width:1180px;margin:0 auto;padding:2rem 1.2rem 4rem;display:grid;grid-template-columns:15.5rem 1fr;gap:2.4rem;align-items:start}
aside{position:sticky;top:5rem;max-height:calc(100vh - 6rem);overflow:auto;padding-right:.4rem;font-size:.88rem}
aside h2{font:600 .72rem/1 var(--sans);letter-spacing:.13em;text-transform:uppercase;color:var(--mute);margin:1.2rem 0 .4rem}
aside ul{list-style:none;margin:0;padding:0}
aside li{margin:.12rem 0}
aside a{display:block;padding:.25rem .5rem;border-radius:8px;text-decoration:none;color:var(--soft)}
aside a:hover{background:var(--panel);color:var(--ink)}
aside a.here{background:var(--panel);color:var(--ink);font-weight:600}
article{max-width:var(--measure);min-width:0}
article h1{font:600 clamp(1.7rem,3.6vw,2.3rem)/1.15 var(--serif);margin:.2rem 0 .8rem;letter-spacing:-.01em}
article h2{font:600 1.34rem/1.25 var(--serif);margin:2.2rem 0 .6rem;padding-top:.4rem;border-top:1px solid var(--line)}
article h3{font:600 1.08rem/1.3 var(--serif);margin:1.6rem 0 .4rem}
article p,article li{color:var(--ink)}
article table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.92rem;display:block;overflow-x:auto}
article th,article td{border:1px solid var(--line);padding:.5rem .6rem;text-align:left;vertical-align:top}
article th{background:var(--panel);font:600 .78rem/1.3 var(--sans);letter-spacing:.04em;text-transform:uppercase;color:var(--mute)}
article blockquote{margin:1.2rem 0;padding:.7rem 1rem;background:var(--panel);border-left:3px solid var(--gold);color:var(--soft)}
article code{font:400 .87em/1.4 var(--mono);background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:.08rem .3rem}
article pre{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:.9rem;overflow:auto}
article hr{border:0;border-top:1px solid var(--line);margin:2rem 0}
article ul,article ol{padding-left:1.3rem}
.kicker{font:600 .74rem/1 var(--sans);letter-spacing:.15em;text-transform:uppercase;color:var(--gold)}
.pager{display:flex;justify-content:space-between;gap:1rem;margin:2.6rem 0 0;padding-top:1rem;border-top:1px solid var(--line);font-size:.9rem}
.banner{background:#fbeede;border:1px solid #d9a44b;border-radius:10px;padding:.8rem 1rem;margin:0 0 1.2rem;font-size:.92rem;color:#6b4a10}
.banner strong{color:#4d3405}
.grid{display:grid;gap:.9rem;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));margin:1.2rem 0}
.card{display:block;text-decoration:none;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:.9rem 1rem}
.card:hover{border-color:var(--gold)}
.card .n{font:600 .72rem/1 var(--sans);letter-spacing:.1em;text-transform:uppercase;color:var(--gold)}
.card h3{margin:.4rem 0 .3rem;font-size:1.02rem}
.card p{margin:0;font-size:.88rem;color:var(--soft)}
footer.site{border-top:1px solid var(--line);padding:1.6rem 1.2rem 3rem;color:var(--mute);font-size:.86rem;max-width:1180px;margin:0 auto}
@media (max-width:900px){main{grid-template-columns:1fr}aside{position:static;max-height:none;border-bottom:1px solid var(--line);padding-bottom:1rem}}
@media print{header.top,aside,.pager{display:none}main{display:block;max-width:none}article{max-width:none}
 body{font-size:11.5pt}article h2{break-after:avoid}article table{break-inside:avoid}}
"""

TITLES = {
    "syllabus": "Syllabus",
    "instructor-guide": "Instructor guide",
    "rubrics": "Rubrics",
    "sources": "Sources",
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def render(md_text: str) -> str:
    MD.reset()
    return MD.convert(md_text)


def nav_html(current: str, instructor_pages: list[tuple[str, str]]) -> str:
    parts = ['<h2>Course</h2><ul>']
    for slug, label in [("index", "Overview"), ("syllabus", "Syllabus")]:
        cls = ' class="here"' if slug == current else ""
        parts.append(f'<li><a href="{slug}.html"{cls}>{label}</a></li>')
    parts.append("</ul><h2>Sessions</h2><ul>")
    for s in CATALOG["sessions"]:
        slug = f"class-{s['n']:02d}"
        cls = ' class="here"' if slug == current else ""
        parts.append(f'<li><a href="{slug}.html"{cls}>{s["n"]}. {s["title"]}</a></li>')
    parts.append("</ul><h2>Assignments</h2><ul>")
    for i in range(1, 16):
        slug = f"homework-{i:02d}"
        cls = ' class="here"' if slug == current else ""
        parts.append(f'<li><a href="{slug}.html"{cls}>Homework {i}</a></li>')
    parts.append("</ul><h2>Exams</h2><ul>")
    for slug, label in [("midterm", "Midterm"), ("final", "Final exam")]:
        cls = ' class="here"' if slug == current else ""
        parts.append(f'<li><a href="{slug}.html"{cls}>{label}</a></li>')
    parts.append("</ul><h2>Reference</h2><ul>")
    for slug in ("rubrics", "sources"):
        cls = ' class="here"' if slug == current else ""
        parts.append(f'<li><a href="{slug}.html"{cls}>{TITLES[slug]}</a></li>')
    if instructor_pages:
        parts.append('<li><a href="instructor/index.html">Instructor material</a></li>')
    parts.append("</ul>")
    return "".join(parts)


def page(title: str, body: str, current: str, instructor_pages: list[tuple[str, str]],
         banner: str = "", pager: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · SOC 4150</title>
<meta name="description" content="SOC 4150 — A Different World: Black Experience and American Society. A 15-session sociology seminar.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<a class="skip" href="#content">Skip to content</a>
<header class="top"><div class="in">
  <a class="brand" href="index.html">SOC 4150 <em>·</em> A Different World</a>
  <nav>
    <a href="index.html">Overview</a>
    <a href="syllabus.html">Syllabus</a>
    <a href="class-01.html">Sessions</a>
    <a href="homework-01.html">Homework</a>
    <a href="midterm.html">Midterm</a>
    <a href="final.html">Final</a>
    <a href="sources.html">Sources</a>
    <a href="https://joenobody-ai.github.io/different-world-notes/v2/" target="_blank" rel="noopener">Reference site</a>
  </nav>
</div></header>
<main>
<aside>{nav_html(current, instructor_pages)}</aside>
<article id="content">
{banner}{body}
{pager}
</article>
</main>
<footer class="site">
  <p><strong>SOC 4150 — A Different World: Black Experience and American Society.</strong>
  Course materials licensed CC BY 4.0: use and adapt them, keep the attribution.
  <em>A Different World</em> is the property of its rights holders; this course teaches about the show and
  reproduces no scripts, stills or footage.</p>
  <p>Built from <code>course/</code> by <code>scripts/build_course.py</code> · verified by
  <code>scripts/verify_course.py</code> · reference site:
  <a href="https://joenobody-ai.github.io/different-world-notes/v2/">different-world-notes</a></p>
</footer>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-instructor", action="store_true",
                    help="omit the exam keys from the built site")
    ap.add_argument("--out", default="docs",
                    help="output directory, relative to the repo root (default: docs, which is what "
                         "GitHub Pages serves from this repository)")
    args = ap.parse_args()

    SITE = ROOT / args.out
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    (SITE / "assets/style.css").write_text(CSS)

    instructor_pages: list[tuple[str, str]] = []

    # --- student-facing pages ---
    plan: list[tuple[pathlib.Path, str]] = []      # (source md, output slug)
    plan.append((COURSE / "syllabus.md", "syllabus"))
    for s in CATALOG["sessions"]:
        plan.append((COURSE / f"class-{s['n']:02d}.md", f"class-{s['n']:02d}"))
    for i in range(1, 16):
        plan.append((COURSE / "assignments" / f"homework-{i:02d}.md", f"homework-{i:02d}"))
    plan.append((COURSE / "exams/midterm.md", "midterm"))
    plan.append((COURSE / "exams/final.md", "final"))
    plan.append((COURSE / "rubrics.md", "rubrics"))
    plan.append((COURSE / "sources.md", "sources"))

    missing = [str(p) for p, _ in plan if not p.exists()]
    if missing:
        print("ERROR: missing course files:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 2

    slugs = [s for _, s in plan]
    for src, slug in plan:
        body = render(src.read_text())
        pager = ""
        idx = slugs.index(slug)
        prev_s = slugs[idx - 1] if idx > 0 else None
        next_s = slugs[idx + 1] if idx < len(slugs) - 1 else None
        labels = dict([(s, s.replace("-", " ").title()) for s in slugs] + [("index", "Overview")])
        if prev_s or next_s:
            left = f'<a href="{prev_s}.html">← {labels.get(prev_s, prev_s)}</a>' if prev_s else "<span></span>"
            right = f'<a href="{next_s}.html">{labels.get(next_s, next_s)} →</a>' if next_s else "<span></span>"
            pager = f'<div class="pager">{left}{right}</div>'
        (SITE / f"{slug}.html").write_text(page(labels.get(slug, slug), body, slug, [], pager=pager))

    # --- index ---
    cards = "".join(
        f'<a class="card" href="class-{s["n"]:02d}.html"><span class="n">Session {s["n"]}</span>'
        f'<h3>{s["title"]}</h3><p>{s["big_question"]}</p></a>'
        for s in CATALOG["sessions"])
    idx_body = f"""<p class="kicker">Sociology · 15 sessions · upper division</p>
<h1><em>A Different World</em>: Black Experience and American Society</h1>
<p><strong>{CATALOG['course']['code']}</strong> · 15 sessions · 75 minutes · renumber to fit your catalogue.</p>
<p>Every session pairs a 2026 Netflix episode with the 1987–1993 original episode it calls back to, and asks
what changed and what did not. The show's own device — the callback — is the course's method. Black
experience is not a specialty bolted onto "general" sociology; it is where the general theory gets tested.</p>
<div class="grid">
  <a class="card" href="syllabus.html"><span class="n">Start here</span><h3>Syllabus</h3>
  <p>Description, outcomes, schedule, assessment, policies</p></a>
  <a class="card" href="instructor-guide.html"><span class="n">For the instructor</span><h3>Instructor guide</h3>
  <p>Norm-setting, the hard conversations, adaptation, the evidence rule</p></a>
  <a class="card" href="midterm.html"><span class="n">Assessment</span><h3>Midterm &amp; final</h3>
  <p>Both exams, with the applied question and the transfer requirement</p></a>
  <a class="card" href="sources.html"><span class="n">Evidence</span><h3>Sources</h3>
  <p>Books by citation; links HTTP-checked on the build date</p></a>
</div>
<h2>The 15 sessions</h2>
<div class="grid">{cards}</div>
<h2>How to use this site</h2>
<p>Students: start with the <a href="syllabus.html">syllabus</a>, then Session 1. Homework is due at the
start of the following session and each assignment says exactly what to hand in and how it is marked.</p>
<p>Instructors: read the <a href="instructor-guide.html">instructor guide</a> before Session 1. Exam keys
are in this repository under <code>course/exams/</code> and, if built, at <code>instructor/index.html</code>
— deliberately not linked from the navigation.</p>
<h2>Evidence rule</h2>
<p>The whole course runs on keeping three things apart: <strong>documented</strong> facts (episode titles,
dates, credits, published summaries), <strong>interpretations</strong> (readings of what a scene or season
argues), and <strong>hypotheses</strong> (claims on the table for testing). Students are graded on it from
week one. The reference site does the same thing, which is why homework points there.</p>"""
    (SITE / "index.html").write_text(page("Overview", render(idx_body) if False else idx_body,
                                         "index", instructor_pages))

    # instructor guide (student-visible page, it is teaching advice not an answer key)
    gsrc = COURSE / "instructor-guide.md"
    (SITE / "instructor-guide.html").write_text(
        page("Instructor guide", render(gsrc.read_text()), "instructor-guide", instructor_pages,
             banner='<div class="banner"><strong>Note:</strong> this page is teaching advice, not exam '
                    'material. It is safe for students to read, but it is written for the instructor.</div>'))

    # --- instructor material (keys) ---
    if not args.no_instructor:
        INS = SITE / "instructor"
        INS.mkdir(exist_ok=True)
        banner = ('<div class="banner"><strong>INSTRUCTOR MATERIAL — do not distribute to students.</strong> '
                  'This page contains model answers and point allocations. It is not linked from the course '
                  'navigation. If this repository is public, either make it private or rebuild with '
                  '<code>--no-instructor</code>.</div>')
        key_pages = [("midterm-key", COURSE / "exams/midterm-key.md", "Midterm key"),
                     ("final-key", COURSE / "exams/final-key.md", "Final key")]
        for slug, src, label in key_pages:
            (INS / f"{slug}.html").write_text(
                page(label, render(src.read_text()), "instructor", instructor_pages, banner=banner))
            instructor_pages.append((slug, label))
        listing = "".join(f'<li><a href="{s}.html">{l}</a></li>' for s, l in instructor_pages)
        (INS / "index.html").write_text(page(
            "Instructor material", f"{banner}<h2>Exam keys</h2><ul>{listing}</ul>"
            "<p>These are generated from <code>course/exams/*-key.md</code>. Rebuild with "
            "<code>python3 scripts/build_course.py --no-instructor</code> to omit them from the site.</p>",
            "instructor", instructor_pages))

    built = sorted(p.name for p in SITE.glob("*.html"))
    print(f"built {len(built)} pages into {SITE}")
    print("  " + " ".join(built))
    if not args.no_instructor:
        print("  NOTE: instructor exam keys were written to site/instructor/ — not linked in the student nav")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
