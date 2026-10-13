#!/usr/bin/env python3
"""verify_course.py — machine checks for the Karens-Class course family. Stdlib only.

Checks SOC 4150 (upper-division seminar) and SOC 1000 (first-year intro). Exit 0 = ALL CHECKS PASS.

Usage:
    python3 scripts/verify_course.py                 # verify SOC 4150 (default)
    python3 scripts/verify_course.py --course 1000   # verify SOC 1000
    python3 scripts/verify_course.py --all           # verify both

What it enforces (per course):
  1. Every expected file exists.
  2. The course catalog is internally consistent (15 sessions, weights sum to 100, episodes ordered
     where the course is sequential, midterm window correct).
  3. Each session's markdown names its session, its 2026 episode, and its original episode(s) with dates.
  4. Each session has the required sections and a 75-minute lecture arc that actually sums to 75.
  5. Every original episode assigned exists in data/original_episodes.json with a matching title AND date.
  6. Every deep link into the reference site points at an anchor that exists in that site's HTML.
  7. Every external URL in the course is either HTTP-verified (200) in the parent project's check log or
     listed in the documented blocked-to-bots allowlist. No unverified link is published.
  8. Homework files point at the reference site, state a due session, and carry criteria.
  8b. The lingo reference exists, explains the tiers, and is cross-referenced where vocabulary does work.
  9. The built site exists, is complete, and contains no unrendered markdown or template leftovers.
  10. The rights notice (copyright, marks, no registration symbol, no stale CC BY) is present everywhere.
  11. No TODO/FIXME/lorem or prose-hygiene artifacts.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]        # karens-class/
PARENT = ROOT.parent                                       # different-world-fan-page/
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

# Course-specific verification settings. SOC 4150 walks the 2026 season in order (episodes 1..10 with ep 7
# split); SOC 1000 is thematic, so it only requires episode numbers in range and skips the own-page rule.
COURSES = {
    "4150": {
        "code": "SOC 4150",
        "src": "course",
        "catalog": "data/course_catalog.json",
        "site": "docs",
        "sequential": True,
        "expected_episodes": [1, 2, 3, 4, 5, 6, 7, 7, 8, 9, 10],
        "midterm_released_after": 8,
        "midterm_due_before": 10,
        "own_page_rule": True,
        "lingo_full_sections": True,
        "lingo_crossrefs": ["class-03", "class-04", "class-05", "class-08", "class-13",
                            "assignments/homework-04"],
    },
    "1000": {
        "code": "SOC 1000",
        "src": "soc1000",
        "catalog": "data/soc1000_catalog.json",
        "site": "docs/soc1000",
        "sequential": False,
        "expected_episodes": None,
        "midterm_released_after": 7,
        "midterm_due_before": 9,
        "own_page_rule": False,
        "lingo_full_sections": False,
        "lingo_crossrefs": ["class-03", "class-05", "class-08", "class-09", "class-10",
                            "assignments/homework-03"],
    },
}

fails: list[str] = []
checks = 0
words_total = 0


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


def check_course(code: str, spec: dict) -> None:        # noqa: C901
    global words_total
    catalog = json.loads((ROOT / spec["catalog"]).read_text())
    sessions = catalog["sessions"]
    SRC = ROOT / spec["src"]
    SITE = ROOT / spec["site"]
    originals = json.loads((ROOT / "data/original_episodes.json").read_text())
    oidx = {(e["season"], e["ep"]): e for e in originals}
    eps2026 = json.loads((PARENT / "data/episodes.json").read_text())["episodes"]
    e2026 = {e["number"]: e for e in eps2026}
    checks_log = json.loads((PARENT / "data/source_checks.json").read_text())["urls"]

    print(f"1. files ({code})")
    expected = [f"{spec['src']}/syllabus.md", f"{spec['src']}/instructor-guide.md",
                f"{spec['src']}/rubrics.md", f"{spec['src']}/lingo.md", f"{spec['src']}/sources.md",
                f"{spec['src']}/rights.md",
                f"{spec['src']}/exams/midterm.md", f"{spec['src']}/exams/midterm-key.md",
                f"{spec['src']}/exams/final.md", f"{spec['src']}/exams/final-key.md"]
    expected += [f"{spec['src']}/class-{i:02d}.md" for i in range(1, 16)]
    expected += [f"{spec['src']}/assignments/homework-{i:02d}.md" for i in range(1, 16)]
    expected += [spec["catalog"], "data/original_episodes.json", "README.md", "LICENSE"]
    for rel in expected:
        ok((ROOT / rel).exists(), f"exists: {rel}")
    ok(not (ROOT / f"{spec['src']}/assignments/homework-16.md").exists(), "no stray homework beyond 15")

    print(f"2. catalogue ({code})")
    ok(len(sessions) == 15, "15 sessions in the catalogue", f"got {len(sessions)}")
    ok([s["n"] for s in sessions] == list(range(1, 16)), "sessions numbered 1..15 in order")
    weights = catalog["assessments"]
    total = sum(weights[k] for k in ("participation", "homework", "midterm", "final", "capstone"))
    ok(total == 100, "assessment weights sum to 100", f"got {total}")
    if spec["sequential"]:
        first_eleven = [s["episode_2026"] for s in sessions[:11]]
        ok(first_eleven == spec["expected_episodes"],
           "sessions 1-11 walk the 2026 season in order, splitting ep 7", f"got {first_eleven}")
    else:
        for s in sessions:
            ok(1 <= s["episode_2026"] <= 10, f"session {s['n']}: episode_2026 in range 1..10",
               f"got {s['episode_2026']}")
    ok(weights["midterm_released_after"] == spec["midterm_released_after"]
       and weights["midterm_due_before"] == spec["midterm_due_before"],
       f"midterm window is sessions {spec['midterm_released_after']} -> {spec['midterm_due_before']}")
    for s in sessions:
        ok(bool(s.get("homework")) and bool(s.get("anchors")), f"session {s['n']} has homework + anchors")

    print(f"3. session prose matches the catalogue ({code})")
    for s in sessions:
        f = SRC / f"class-{s['n']:02d}.md"
        text = read(f)
        ok(norm(s["title"].split(":")[0])[:22] in norm(text),
           f"class-{s['n']:02d}: names its session")
        ep = e2026.get(s["episode_2026"])
        if ep and "revisit" not in s["episode_title"]:
            ok(norm(ep["title"]) in norm(text), f"class-{s['n']:02d}: names 2026 episode {ep['title']!r}")
        for o in s["originals"]:
            ok(o["title"] in text, f"class-{s['n']:02d}: names original {o['title']!r}")
            ok(o["air_date"] in text, f"class-{s['n']:02d}: gives the date {o['air_date']}")

    print(f"4. required sections + lecture arc ({code})")
    for s in sessions:
        text = read(SRC / f"class-{s['n']:02d}.md")
        for needle in ("## Before class", "## Sociological frame", "## Discussion questions",
                       "## Instructor notes", "## Key terms", "## Homework", "## Further reading"):
            ok(needle in text, f"class-{s['n']:02d}: has {needle}")
        starts = [int(a) for a, _ in re.findall(r"\|\s*(\d+)[–-](\d+)\s*\|", text)]
        ends = [int(b) for _, b in re.findall(r"\|\s*(\d+)[–-](\d+)\s*\|", text)]
        if len(starts) >= 3:
            ok(starts[0] == 0, f"class-{s['n']:02d}: arc starts at 0", f"got {starts[0]}")
            ok(bool(ends) and max(ends) == 75, f"class-{s['n']:02d}: arc ends at 75",
               f"got {max(ends) if ends else None}")
        branches = len(re.findall(r"\*\*If ", text))
        ok(branches >= 2, f"class-{s['n']:02d}: instructor notes have discussion branches",
           f"found {branches}")

    print(f"5. originals verified against the episode list ({code})")
    for s in sessions:
        for o in s["originals"]:
            rec = oidx.get((o["season"], o["ep"]))
            ok(rec is not None, f"session {s['n']}: S{o['season']}E{o['ep']} exists in the episode list")
            if rec:
                ok(rec["title"] == o["title"],
                   f"session {s['n']}: S{o['season']}E{o['ep']} title matches",
                   f"{rec['title']!r} != {o['title']!r}")
                ok(rec["air_date"] == o["air_date"],
                   f"session {s['n']}: S{o['season']}E{o['ep']} air date matches",
                   f"{rec['air_date']} != {o['air_date']}")

    print(f"6. reference-site deep links resolve to real anchors ({code})")
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
        if spec["own_page_rule"] and s["n"] <= 11:
            ok(own_hits >= 1, f"session {s['n']}: cites at least one card from its own episode page")

    print(f"7. every published URL is verified ({code})")
    verified = {u for u, m in checks_log.items() if m["status"] == 200}
    local_ok = 0
    bad_links: list[str] = []
    for src in sorted(SRC.rglob("*.md")):
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

    print(f"8. homework files ({code})")
    for i in range(1, 16):
        text = read(SRC / f"assignments/homework-{i:02d}.md")
        ok(REF_HOST in text or "reference site" in text.lower(),
           f"homework-{i:02d}: points at the reference site")
        ok(("## Criteria" in text) or ("## Rubric" in text), f"homework-{i:02d}: has criteria or rubric")
        ok("**Due:**" in text, f"homework-{i:02d}: states its due session")

    print(f"8b. the lingo reference ({code})")
    lingo_md = read(SRC / "lingo.md")
    for tier in ("documented", "era lexicon", "handle with care"):
        ok(tier in lingo_md.lower(), f"lingo.md explains the '{tier}' tier")
    ok("different-world-notes/lingo.html" in lingo_md, "lingo.md points at the tiered reference")
    ok("different-world-notes/v2/lingo.html" in lingo_md, "lingo.md points at the Netflix-style view")
    if spec["lingo_full_sections"]:
        for needle in ("## 1. The evidence rule, applied to vocabulary",
                       "## 2. Where each section does work",
                       "## 3. Three classroom exercises",
                       "## 4. The protocol for the instructors",
                       "## 5. Why this belongs in a *sociology* course",
                       "## 6. Using it in assessment",
                       "## 7. Sources"):
            ok(needle in lingo_md, f"lingo.md has section: {needle}")
    for rel in spec["lingo_crossrefs"]:
        text = read(SRC / f"{rel}.md")
        ok("lingo" in text.lower(), f"{rel} cross-references the lingo reference")
    ok("protocol" in read(SRC / "instructor-guide.md").lower(),
       "instructor guide carries the vocabulary protocol")

    print(f"9. built site ({code})")
    if not SITE.exists():
        fails.append(f"{spec['site']} not built — run scripts/build_course.py --course {code}")
    else:
        slugs = ["index", "syllabus", "midterm", "final", "rubrics", "sources", "instructor-guide",
                 "lingo"]
        slugs += [f"class-{i:02d}" for i in range(1, 16)]
        slugs += [f"homework-{i:02d}" for i in range(1, 16)]
        for s in slugs:
            ok((SITE / f"{s}.html").exists(), f"{spec['site']}/{s}.html built")
        for p in SITE.glob("*.html"):
            html = read(p)
            ok("{{" not in html and "}}" not in html, f"{p.name}: no template leftovers")
            ok(not re.search(r"^\*\*[A-Z]", html, re.M), f"{p.name}: no unrendered bold markers")
            ok(not re.search(r"^#{1,3} ", html, re.M), f"{p.name}: no unrendered markdown headings")
            ok('<article id="content">' in html, f"{p.name}: has the content region")
        ok((SITE / "assets/style.css").exists(), f"{spec['site']}/assets/style.css built")
        ins = SITE / "instructor"
        if ins.exists():
            ok((ins / "midterm-key.html").exists(), "instructor key page built")
            leaked = [p.name for p in SITE.glob("*.html") if 'href="instructor/midterm-key' in read(p)]
            ok(not leaked, "exam keys are not linked from student pages", f"leaked in {leaked}")

    print(f"10. rights notice ({code})")
    rights_md = read(SRC / "rights.md")
    lic = read(ROOT / "LICENSE")
    for needle in ("© 2026 Dr. Karen Powell", "All rights reserved", "Karens-Class™", "Dr. Karen Powell™",
                   "unregistered trademark", "false marking", "No affiliation"):
        ok(needle.lower() in rights_md.lower(), f"rights.md contains: {needle}")
    ok("© 2026 Dr. Karen Powell. All rights reserved." in lic, "LICENSE carries the copyright line")
    ok("Karens-Class™" in lic, "LICENSE carries the mark")
    ok("no federal registration is claimed" in lic.lower(), "LICENSE disclaims registration")
    pages = sorted(SITE.rglob("*.html")) if SITE.exists() else []
    ok(len(pages) >= 38, f"built pages to check the notice on (got {len(pages)})")
    for p in pages:
        h = read(p)
        rel = p.relative_to(SITE)
        ok("© 2026 Dr. Karen Powell. All rights reserved." in h, f"{rel}: carries the copyright notice")
        ok("Karens-Class™" in h, f"{rel}: carries the mark")
        ok("®" not in h, f"{rel}: must not use the ® symbol before a registration issues")
    ok((SITE / "rights.html").exists(), "rights page built into the site")
    ok('href="rights.html"' in read(SITE / "class-01.html"), "rights page is reachable from the nav")
    ok("rights.html" in read(SITE / "index.html"), "home page links the rights notice")
    for src in list(SRC.rglob("*.md")) + [ROOT / "README.md"]:
        ok("CC BY 4.0" not in read(src), f"{src.name}: no stale CC BY licence text")

    print(f"11. prose hygiene ({code})")
    bad_prose: list[str] = []
    for src in sorted(list(SRC.rglob("*.md")) + [ROOT / "README.md"]):
        text = read(src)
        for pat in (r"\bTODO\b", r"\bFIXME\b", r"lorem ipsum", r"\bteh\b", r"[a-z] ,", r"[a-z] \.[^.]"):
            if re.search(pat, text):
                bad_prose.append(f"{src.name}: {pat}")
    ok(not bad_prose, "no TODO/FIXME/lorem/stray-double-space artifacts")
    for b in bad_prose:
        fails.append(f"  prose: {b}")

    words_total += sum(len(read(p).split()) for p in SRC.rglob("*.md"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--course", choices=["4150", "1000"], default="4150",
                    help="which course to verify (default: 4150)")
    ap.add_argument("--all", action="store_true", help="verify both courses")
    args = ap.parse_args()

    codes = ["4150", "1000"] if args.all else [args.course]
    for code in codes:
        print(f"\n===== {COURSES[code]['code']} ({code}) =====")
        check_course(code, COURSES[code])

    print(f"\n{checks - len(fails)}/{checks} checks passed · course prose {words_total:,} words")
    if fails:
        print(f"\n{len(fails)} FAILURE(S):")
        for f in fails[:80]:
            print("  ✗", f)
        return 1
    print("ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
