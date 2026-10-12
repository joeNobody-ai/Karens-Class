#!/usr/bin/env bash
# live_check.sh — poll until GitHub Pages has rebuilt, then verify the deployed content.
set -u
B=https://joenobody-ai.github.io/Karens-Class
for i in $(seq 1 14); do
  curl -s -L "$B/sources.html" -o /tmp/live.html
  waf=$(grep -c 'WAF block' /tmp/live.html)
  echo "attempt $i: WAF mentions on sources.html = $waf"
  if [ "$waf" -gt 0 ]; then break; fi
  sleep 15
done
echo "--- deployed content check ---"
curl -s -L "$B/instructor-guide.html" -o /tmp/live2.html
printf "sources.html      : %s  · WAF blocks named: %s · 'blocked to automated' heading: %s\n" \
  "$(curl -s -o /dev/null -w '%{http_code}' -L "$B/sources.html")" \
  "$(grep -c 'WAF block' /tmp/live.html)" \
  "$(grep -c 'blocked to automated checks' /tmp/live.html)"
printf "instructor-guide  : %s  · nmaahc mention: %s · 'Archives worth a browser tab': %s\n" \
  "$(curl -s -o /dev/null -w '%{http_code}' -L "$B/instructor-guide.html")" \
  "$(grep -c 'nmaahc' /tmp/live2.html)" \
  "$(grep -c 'Archives worth a browser tab' /tmp/live2.html)"
printf "home page         : %s\n" "$(curl -s -o /dev/null -w '%{http_code}' -L "$B/")"
printf "class-15 (rebuilt): %s  · arc ends at 75 check present: %s\n" \
  "$(curl -s -o /dev/null -w '%{http_code}' -L "$B/class-15.html")" \
  "$(grep -c 'revised rather than defended' <(curl -s -L "$B/class-15.html"))"
