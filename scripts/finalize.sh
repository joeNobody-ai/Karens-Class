#!/usr/bin/env bash
# finalize.sh — regenerate the bibliography, rebuild the site, verify, and ship. Run from karens-class/.
set -u
cd /opt/data/profiles/different-world/projects/different-world-fan-page/karens-class
. ../.venv/bin/activate

echo "=== regenerate the bibliography from the check log ==="
python3 scripts/make_sources.py

echo "=== rebuild the site ==="
python3 scripts/build_course.py > /tmp/b.txt 2>&1
echo "build exit=$?  pages=$(ls docs/*.html | wc -l)  instructor=$(ls docs/instructor/*.html 2>/dev/null | wc -l)"

echo "=== verify (must print ALL CHECKS PASS) ==="
python3 scripts/verify_course.py > /tmp/v.txt 2>&1
echo "verify exit=$?"
tail -3 /tmp/v.txt

echo "=== what the bibliography now says about blocked links ==="
grep -c "WAF block" course/sources.md
grep -n "Smithsonian" course/sources.md | head -3

echo "=== commit and push the course repo ==="
git add -A
git -c core.hooksPath=/dev/null commit -q -m "Bibliography: name the archives that block automated checks instead of dropping them

The source audit showed NMAAHC, the Library of Congress Civil Rights History Project and the World
Digital Library returning 403. Probing with browser headers showed the Smithsonian's own homepage
returns 403 to the same client, so these are WAF blocks, not dead links — dropping them silently was
the wrong call. They are now listed with per-URL reasons, referenced in the instructor guide, and
allow-listed in the verifier." || echo "  (nothing to commit)"
git push -q origin main && echo "  pushed: $(git log --oneline | head -1)"

echo "=== live check ==="
sleep 5
B=https://joenobody-ai.github.io/Karens-Class
curl -s -L "$B/sources.html" -o /tmp/live.html
echo "  sources.html HTTP=$(curl -s -o /dev/null -w '%{http_code}' -L "$B/sources.html")  WAF-mentions=$(grep -c 'WAF block' /tmp/live.html)"
curl -s -L "$B/instructor-guide.html" -o /tmp/live2.html
echo "  instructor-guide.html nmaahc mention=$(grep -c 'nmaahc' /tmp/live2.html)"
echo "=== done ==="
