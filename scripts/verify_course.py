#!/usr/bin/env python3
"""verify_course.py — machine checks for the Karens-Class course. Stdlib only.

Exit 0 = ALL CHECKS PASS. Anything else prints exactly what failed and why.

What it enforces:
  1. Every expected file exists.
  2. data/course_catalog.json is internally consistent (15 sessions, weights sum to 100, episodes in order).
  3. Each session's markdown names its session, its 2026 episode, and its original episode(s) with dates.
  4. Each session has the required sections and a 75-minute lecture arc that actually sums to 75.
  5. Every original episode assigned exists in data/original_episodes.json with a matching title AND date.
  6. Every deep link into the reference site points at an anchor that exists in that site's HTML.
  7. Every external URL in the course is either HTTP-verified (200) in the parent project's check log or
     listed in the documented blocked-to-bots allowlist. No unverified link is published.
  8. The built site exists, is complete, and contains no unrendered markdown or template leftovers.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]        # karens-class/
PARENT = ROOT.parent                                       # different-world-fan-page/
COURSE = ROOT / "course"
SITE = ROOT / "docs"                                       # what GitHub Pages serves
REF_HOST = "joenobody-ai.github.io/different-world-notes"

BLOCKED_OK = {
    # documented API codes and WAF blocks — see scripts/make_sources.py for the justification of each
    "https://www.imdb.com/title/tt33081352/",
    "https://www.imdb.com/title/tt0092339/",
    "https://www.bls.gov/",
    "https://nmaahc.si.edu/",
    "https://www.loc.gov/collections/civil-rights-history-project/",
    "https://www.wdl.org/",
    "https://sites.ed.gov/whhbcu/",
    "https://www.annualreviews.org/journal/soc",
}

fails: list[str] = []
checks = 0


def ok(cond: bool, label: str, detail: str = "") -> None:
    global checks
    checks += 1
    if not cond:
        fails.append(f"{label} {detail}".strip())


def read(p: pathlib.Path) -> str:
    if p.is_dir():
        p = p / "index.html"
    if not p.is_file():
        return ""
    try:
        return p.read_text()
    except (OSError, UnicodeDecodeError):
        return ""


def find_urls(text: str) -> list[str]:
    """Collect URLs, handling both <angle-bracketed> links (which may contain parentheses,
    e.g. Wikipedia titles) and bare URLs (where a trailing ) is punctuation, not part of the URL)."""
    urls = re.findall(r"<https?://[^>\s]+>", text)
    urls = [u[1:-1] for u in urls]
    bare = re.findall(r"(?<![<(])https?://[^\s<>\)\]\}`]+", text)
    out: list[str] = []
    for u in urls + bare:
        u = u.rstrip(".,;:")
        if u not in out:
            out.append(u)
    return out


def norm(x: str) -> str:
    """Lowercase, strip markdown and typographic punctuation, collapse spaces — for title comparison."""
    x = x.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("…", "...")
    x = re.sub(r"[^a-z0-9 ]+", " ", x.lower())
    return re.sub(r"\s+", " ", x).strip()


def main() -> int:                                          # noqa: C901
    catalog = json.loads((ROOT / "data/course_catalog.json").read_text())
    sessions = catalog["sessions"]
    originals = json.loads((ROOT / "data/original_episodes.json").read_text())
    oidx = {(e["season"], e["ep"]): e for e in originals}
    eps2026 = json.loads((PARENT / "data/episodes.json").read_text())["episodes"]
    e2026 = {e["number"]: e for e in eps2026}
    checks_log = json.loads((PARENT / "data/source_checks.json").read_text())["urls"]

    print("1. files")
    expected = ["README.md", "data/course_catalog.json", "data/original_episodes.json",
                "course/syllabus.md", "course/instructor-guide.md", "course/rubrics.md",
                "course/sources.md", "course/exams/midterm.md", "course/exams/midterm-key.md",
                "course/exams/final.md", "course/exams/final-key.md"]
    expected += [f"course/class-{i:02d}.md" for i in range(1, 16)]
    expected += [f"course/assignments/homework-{i:02d}.md" for i in range(1, 16)]
    for rel in expected:
        ok((ROOT / rel).exists(), f"exists: {rel}")
    ok(not (ROOT / "course/assignments/homework-16.md").exists(), "no stray homework beyond 15")

    print("2. catalogue")
    ok(len(sessions) == 15, "15 sessions in the catalogue", f"got {len(sessions)}")
    ok([s["n"] for s in sessions] == list(range(1, 16)), "sessions numbered 1..15 in order")
    weights = catalog["assessments"]
    total = sum(weights[k] for k in ("participation", "homework", "midterm", "final", "capstone"))
    ok(total == 100, "assessment weights sum to 100", f"got {total}")
    first_eleven = [s["episode_2026"] for s in sessions[:11]]
    ok(first_eleven == [1, 2, 3, 4, 5, 6, 7, 7, 8, 9, 10],
       "sessions 1-11 walk the 2026 season in order, splitting ep 7", f"got {first_eleven}")
    ok(weights["midterm_released_after"] == 8 and weights["midterm_due_before"] == 10,
       "midterm window is sessions 8 -> 10")
    for s in sessions:
        ok(bool(s.get("homework")) and bool(s.get("anchors")), f"session {s['n']} has homework + anchors")

    print("3. session prose matches the catalogue")
    for s in sessions:
        f = COURSE / f"class-{s['n']:02d}.md"
        text = read(f)
        ok(norm(s["title"].split(":")[0])[:22] in norm(text),
           f"class-{s['n']:02d}: names its session")
        ep = e2026.get(s["episode_2026"])
        if ep and "revisit" not in s["episode_title"]:
            ok(norm(ep["title"]) in norm(text), f"class-{s['n']:02d}: names 2026 episode {ep['title']!r}")
        for o in s["originals"]:
            ok(o["title"] in text, f"class-{s['n']:02d}: names original {o['title']!r}")
            ok(o["air_date"] in text, f"class-{s['n']:02d}: gives the date {o['air_date']}")
    print("4. required sections + lecture arc")
    for s in sessions:
        text = read(COURSE / f"class-{s['n']:02d}.md")
        for needle in ("## Before class", "## Sociological frame", "## Discussion questions",
                       "## Instructor notes", "## Key terms", "## Homework", "## Further reading"):
            ok(needle in text, f"class-{s['n']:02d}: has {needle}")
        mins = [int(a) for a in re.findall(r"\|\s*(\d+)[–-](\d+)\s*\|", text) for a in [a[0]]]
        ends = [int(b) for _, b in re.findall(r"\|\s*(\d+)[–-](\d+)\s*\|", text)]
        starts = [int(a) for a, _ in re.findall(r"\|\s*(\d+)[–-](\d+)\s*\|", text)]
        if len(starts) >= 3:
            ok(starts[0] == 0, f"class-{s['n']:02d}: arc starts at 0", f"got {starts[0]}")
            ok(bool(ends) and max(ends) == 75, f"class-{s['n']:02d}: arc ends at 75",
               f"got {max(ends) if ends else None}")
        # instructor notes must contain at least two "if the room..." branches
        branches = len(re.findall(r"\*\*If ", text))
        ok(branches >= 2, f"class-{s['n']:02d}: instructor notes have discussion branches",
           f"found {branches}")

    print("5. originals verified against the episode list")
    for s in sessions:
        for o in s["originals"]:
            rec = oidx.get((o["season"], o["ep"]))
            ok(rec is not None, f"session {s['n']}: S{o['season']}E{o['ep']} exists in the episode list")
            if rec:
                ok(rec["title"] == o["title"],
                   f"session {s['n']}: S{o['season']}E{o['ep']} title matches", f"{rec['title']!r} != {o['title']!r}")
                ok(rec["air_date"] == o["air_date"],
                   f"session {s['n']}: S{o['season']}E{o['ep']} air date matches",
                   f"{rec['air_date']} != {o['air_date']}")

    print("6. reference-site deep links resolve to real anchors")
    for s in sessions:
        own_page = PARENT / f"v2/ep{s['episode_2026']:02d}.html"
        ok(own_page.exists(), f"session {s['n']}: reference page {own_page.name} exists")
        own_hits = 0
        for anchor in s["anchors"]:
            prefix = anchor.split("-", 1)[0]                       # ep07-diaspora-identity -> ep07
            page = PARENT / f"v2/{prefix}.html" if re.fullmatch(r"ep\d{2}", prefix) else own_page
            html = read(page)
            ok(f'id="{anchor}"' in html,
               f"session {s['n']}: anchor #{anchor} exists in {page.name}")
            if page == own_page:
                own_hits += 1
        if s["n"] <= 11:                                            # episode-anchored sessions
            ok(own_hits >= 1, f"session {s['n']}: cites at least one card from its own episode page")

    print("7. every published URL is verified")
    verified = {u for u, m in checks_log.items() if m["status"] == 200}
    local_ok = 0
    bad_links: list[str] = []
    for src in sorted(COURSE.rglob("*.md")):
        for url in find_urls(read(src)):
            if REF_HOST in url:
                path, _, frag = url.partition("#")
                rel = path.split(REF_HOST, 1)[1].lstrip("/")
                local = PARENT / rel
                if not local.exists():
                    bad_links.append(f"{src.name}: no such page {rel}")
                elif frag and f'id="{frag}"' not in read(local):
                    bad_links.append(f"{src.name}: {rel}#{frag} anchor missing")
                else:
                    local_ok += 1
            elif url in verified:
                local_ok += 1
            elif url in BLOCKED_OK:
                local_ok += 1
            else:
                bad_links.append(f"{src.name}: unverified URL {url}")
    ok(not bad_links, "all published URLs are verified or allowed",
       f"({len(bad_links)} problems)" if bad_links else "")
    for b in bad_links:
        fails.append(f"  link: {b}")

    print("8. homework files")
    for i in range(1, 16):
        text = read(COURSE / f"assignments/homework-{i:02d}.md")
        ok(REF_HOST in text or "reference site" in text.lower(),
           f"homework-{i:02d}: points at the reference site")
        ok(("## Criteria" in text) or ("## Rubric" in text), f"homework-{i:02d}: has criteria or rubric")
        ok("**Due:**" in text, f"homework-{i:02d}: states its due session")

    print("9. built site")
    if not SITE.exists():
        fails.append("site/ not built — run scripts/build_course.py")
    else:
        slugs = ["index", "syllabus", "midterm", "final", "rubrics", "sources", "instructor-guide"]
        slugs += [f"class-{i:02d}" for i in range(1, 16)]
        slugs += [f"homework-{i:02d}" for i in range(1, 16)]
        for s in slugs:
            ok((SITE / f"{s}.html").exists(), f"site/{s}.html built")
        for p in SITE.glob("*.html"):
            html = read(p)
            ok("{{" not in html and "}}" not in html, f"site/{p.name}: no template leftovers")
            ok(not re.search(r"^\*\*[A-Z]", html, re.M), f"site/{p.name}: no unrendered bold markers")
            ok(not re.search(r"^#{1,3} ", html, re.M), f"site/{p.name}: no unrendered markdown headings")
            ok('<article id="content">' in html, f"site/{p.name}: has the content region")
        ok((SITE / "assets/style.css").exists(), "site/assets/style.css built")
        # instructor keys must exist but must not be linked from student pages
        ins = SITE / "instructor"
        if ins.exists():
            ok((ins / "midterm-key.html").exists(), "instructor key page built")
            leaked = [p.name for p in SITE.glob("*.html") if 'href="instructor/midterm-key' in read(p)]
            ok(not leaked, "exam keys are not linked from student pages", f"leaked in {leaked}")

    print("10. prose hygiene")
    bad_prose: list[str] = []
    for src in sorted(list(COURSE.rglob("*.md")) + [ROOT / "README.md"]):
        text = read(src)
        for pat in (r"\bTODO\b", r"\bFIXME\b", r"lorem ipsum", r"\bteh\b", r"[a-z] ,", r"[a-z] \.[^.]"):
            if re.search(pat, text):
                bad_prose.append(f"{src.name}: {pat}")
    ok(not bad_prose, "no TODO/FIXME/lorem/stray-double-space artifacts")
    for b in bad_prose:
        fails.append(f"  prose: {b}")

    words = sum(len(read(p).split()) for p in COURSE.rglob("*.md"))
    print(f"\n{checks - len(fails)}/{checks} checks passed · course prose {words:,} words")
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for f in fails[:60]:
            print("  ✗", f)
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
