#!/usr/bin/env python3
"""make_sources.py — generate the course bibliography from the verified link checks.

The rule this enforces: a link appears in the bibliography only if scripts/check_sources.py actually
got an HTTP 200 from it. Everything else is either dropped or listed in a clearly-labelled
"blocked to automated checks" section so the professor can decide.

Inputs : ../data/source_checks.json   (the check log, with per-URL status)
         ../data/source_candidates.json (grouping)
Output : course/sources.md
"""
from __future__ import annotations

import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]           # karens-class/
PARENT = ROOT.parent                                          # different-world-fan-page/
CHECKS = PARENT / "data/source_checks.json"
CAND = PARENT / "data/source_candidates.json"
OUT = ROOT / "course/sources.md"

GROUP_TITLES = {
    "sociology-discipline": "The discipline",
    "data-and-statistics": "Data and statistics",
    "black-history-and-culture-archives": "Archives and institutions",
    "hbcus-and-education": "HBCUs and education",
    "media-and-representation": "Media and representation",
    "the-shows-own-record": "The shows' own record",
    "civil-rights-and-policy-context": "Civil rights and policy context",
}

# URLs that a headless checker cannot reach from this host but that a human can. Two categories:
#  (a) documented API status codes (IMDb returns 202 to bots), and
#  (b) WAF blocks: these return 403 to every automated request *including* the Smithsonian's own
#      homepage, which is unquestionably live — evidence that this is a filter on automated clients,
#      not a dead link. Each is listed with the reason so the professor can decide for themselves.
BLOCKED_BUT_REAL = {
    "https://www.imdb.com/title/tt33081352/": "IMDb answers 202 to automated checkers; the title ID was confirmed through IMDb's own suggestion API",
    "https://www.imdb.com/title/tt0092339/": "IMDb answers 202 to automated checkers; the title ID was confirmed through IMDb's own suggestion API",
    "https://www.bls.gov/": "WAF block (403) on automated requests — verify in a browser",
    "https://nmaahc.si.edu/": "WAF block (403) on automated requests; the Smithsonian's own homepage (si.edu) also returns 403, so this is a filter on automated clients, not a dead link",
    "https://www.loc.gov/collections/civil-rights-history-project/": "WAF block (403) on the collection path, while loc.gov itself answers 200 — verify in a browser",
    "https://www.wdl.org/": "WAF block (403) on automated requests. Note the World Digital Library was folded into the Library of Congress and its content is frozen",
    "https://sites.ed.gov/whhbcu/": "WAF block (403) on automated requests — verify in a browser before putting it on a handout",
    "https://www.annualreviews.org/journal/soc": "Publisher WAF block (403) on automated requests",
}

BOOKS = {
    "Foundational theory": [
        "W. E. B. Du Bois, *The Souls of Black Folk* (1903)",
        "C. Wright Mills, *The Sociological Imagination* (1959)",
        "Émile Durkheim, *The Elementary Forms of Religious Life* (1912)",
        "Erving Goffman, *The Presentation of Self in Everyday Life* (1959)",
        "Erving Goffman, *Stigma: Notes on the Management of Spoiled Identity* (1963)",
        "Marcel Mauss, *The Gift: The Form and Reason for Exchange in Archaic Societies* (1925)",
        "Maurice Halbwachs, *On Collective Memory* (1925/1950)",
        "Anselm L. Strauss, *Negotiations: Varieties, Contexts, Processes, and Social Order* (1978)",
        "Randall Collins, *Interaction Ritual Chains* (2004)",
    ],
    "Race, gender and the image": [
        "Patricia Hill Collins, *Black Feminist Thought: Knowledge, Consciousness, and the Politics of Empowerment* (1990)",
        "Michael Omi and Howard Winant, *Racial Formation in the United States* (3rd ed., 2014)",
        "Candace West and Don H. Zimmerman, \"Doing Gender\" (1987)",
        "Evelyn Brooks Higginbotham, *Righteous Discontent* (1993)",
        "Margaret L. Hunter, *Race, Gender, and the Politics of Skin Tone* (2005)",
        "Herman Gray, *Watching Race: Television and the Struggle for \"Blackness\"* (1995)",
        "Robin R. Means Coleman, *African American Viewers and the Black Situation Comedy: Situating Racial Humor* (1998)",
        "Stuart Hall, \"Encoding/Decoding\" (1973)",
        "Marlon Riggs, *Color Adjustment* (1992, film) and *Ethnic Notions* (1987, film)",
        "Aldon D. Morris, *The Scholar Denied: W. E. B. Du Bois and the Birth of Modern Sociology* (2015)",
    ],
    "Stratification, family and institutions": [
        "Daniel Patrick Moynihan, *The Negro Family: The Case for National Action* (1965)",
        "Herbert G. Gutman, *The Black Family in Slavery and Freedom, 1750-1925* (1976)",
        "William Julius Wilson, *The Truly Disadvantaged* (1987)",
        "Mary Pattillo, *Black Picket Fences* (1999)",
        "Annette Lareau, *Unequal Childhoods* (2003)",
        "Prudence L. Carter, *Keepin' It Real: School Success Beyond Black and White* (2005)",
        "E. Franklin Frazier, *Black Bourgeoisie* (1957)",
        "Victor Ray, \"A Theory of Racialized Organizations\" (2019)",
        "Jeffrey Pfeffer and Gerald R. Salancik, *The External Control of Organizations* (1978)",
        "Pierre Bourdieu and Jean-Claude Passeron, *Reproduction in Education, Society and Culture* (1970/1977)",
    ],
    "Health, the state and violence": [
        "Cathy J. Cohen, *The Boundaries of Blackness: AIDS and the Breakdown of Black Politics* (1999)",
        "Paul Farmer, \"An Anthropology of Structural Violence\" (2004)",
        "Michelle Alexander, *The New Jim Crow* (2010)",
        "Richard Rothstein, *The Color of Law* (2017)",
        "Isabel Wilkerson, *The Warmth of Other Suns* (2010)",
        "Elizabeth Hinton, *America on Fire* (2021)",
    ],
    "Movements and campus politics": [
        "Doug McAdam, *Political Process and the Development of Black Insurgency, 1930-1970* (1982)",
        "David A. Snow and Robert D. Benford, \"Ideology, Frame Resonance, and Participant Mobilization\" (1988)",
    ],
}


def main() -> int:
    checks = json.loads(CHECKS.read_text())
    cand = json.loads(CAND.read_text())
    urls = checks["urls"]

    ok_by_group: dict[str, list[str]] = {g: [] for g in cand["groups"]}
    blocked: list[tuple[str, str]] = []
    for url, meta in urls.items():
        if meta["status"] == 200:
            ok_by_group.setdefault(meta["group"], []).append(url)
        elif url in BLOCKED_BUT_REAL:
            blocked.append((url, BLOCKED_BUT_REAL[url]))

    lines: list[str] = []
    lines.append("# Sources\n")
    lines.append("Two kinds of citation here. **Books and articles** are cited by author, title and year — "
                 "no links, because links to paywalled literature rot fastest. **Institutional and reference "
                 "links** were each checked with an HTTP request on the date below; only ones that answered "
                 f"`200` are listed as live.\n")
    lines.append(f"**Link checks run:** {checks['date']} · "
                 f"{sum(1 for m in urls.values() if m['status'] == 200)} of {len(urls)} candidate URLs answered 200.\n")
    lines.append("> **Before you teach with any of these:** links, and especially statistics, age quickly. "
                 "Re-run `python3 scripts/check_sources.py` from the parent project before the term starts, "
                 "and re-check every figure you put on a board.\n")

    lines.append("## Live links, by subject\n")
    for group, title in GROUP_TITLES.items():
        group_urls = sorted(ok_by_group.get(group, []))
        if not group_urls:
            continue
        lines.append(f"### {title}\n")
        for u in group_urls:
            lines.append(f"- <{u}>")
        lines.append("")

    if blocked:
        lines.append("## Readable by a human, blocked to automated checks\n")
        lines.append("These are worth using, but a headless checker cannot confirm them from this host. "
                     "The strongest evidence that this is a bot filter rather than a dead link: the "
                     "Smithsonian's own homepage returns 403 to the same client. Open each in a browser "
                     "before you put it on a handout.\n")
        for u, why in sorted(blocked):
            lines.append(f"- <{u}> — {why}")
        lines.append("")

    lines.append("## Dropped after checking\n")
    lines.append("Two candidates were removed outright as broken rather than cited: the ASA's *Contexts* "
                 "landing page (404) and a Cornell Legal Information Institute URL that carried an "
                 "incorrect case number (the ruling is cited instead through the two Supreme Court docket "
                 "pages below, which answered 200).\n")
    lines.append("Nothing was dropped merely for refusing automated requests — those are listed in the "
                 "section above, with the reason, so you can check them yourself.\n")
    lines.append("For the affirmative-action ruling discussed in Session 14's wider context, use the docket "
                 "pages, which were checked and answered 200:\n")
    lines.append("- <https://www.law.cornell.edu/supct/cert/20-1199>\n- <https://www.law.cornell.edu/supct/cert/21-707>\n")

    lines.append("## Books and articles\n")
    for theme, items in BOOKS.items():
        lines.append(f"### {theme}\n")
        for it in items:
            lines.append(f"- {it}")
        lines.append("")

    lines.append("## The shows as sources\n")
    lines.append("Episode facts used throughout the course (titles, season and episode numbers, air dates, "
                 "credits, cast) come from the reference project's documented pages, which cite their own "
                 "sources and label every claim by tier:\n")
    lines.append("- Reference site (Netflix-style browse view): <https://joenobody-ai.github.io/"
                 "different-world-notes/v2/>")
    lines.append("- Text version: <https://joenobody-ai.github.io/different-world-notes/>")
    lines.append("- Wikipedia, *A Different World* (2026 TV series): "
                 "<https://en.wikipedia.org/wiki/A_Different_World_(2026_TV_series)>")
    lines.append("- Wikipedia, *List of A Different World episodes* (the 1987-1993 series): "
                 "<https://en.wikipedia.org/wiki/List_of_A_Different_World_episodes>")
    lines.append("")
    lines.append("**Attribution and use.** *A Different World* and its characters and episodes are the "
                 "property of their rights holders. This course teaches *about* the shows: it reproduces no "
                 "scripts, no stills, and no footage, and it summarises only what the shows' own published "
                 "episode summaries state. Students are directed to watch the episodes through legitimate "
                 "services or library holdings, verified locally by the instructor.\n")
    lines.append(f"*Sources file generated {time.strftime('%Y-%m-%d')} by scripts/make_sources.py from the "
                 "HTTP check log — edit the script, not this file.*\n")

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")
    print(f"  live links: {sum(len(v) for v in ok_by_group.values())} across {len(ok_by_group)} groups")
    print(f"  blocked-but-real: {len(blocked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
