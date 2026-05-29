#!/usr/bin/env bash

set -u

GREEN="\033[1;32m"
BLUE="\033[1;34m"
RED="\033[1;31m"
CYAN="\033[1;36m"
DIM="\033[2m"
RESET="\033[0m"
BOLD="\033[1m"

APP="ĥ⁴č̣ƙ Ťĥɛ Płªɲəŧ :: Matrix Audit"
KEYDIR="$HOME/.matrix_keys"

declare -A RESULTS=(
  [headers]=0
  [tls]=0
  [cors]=0
  [methods]=0
  [cache]=0
)

pause() {
  echo
  read -r -p "Press Enter to continue..."
}

cleanup() {
  [[ -n "${RAIN_PID:-}" ]] && kill "$RAIN_PID" 2>/dev/null || true
  tput cnorm 2>/dev/null || true
  clear
}
trap cleanup EXIT INT TERM

# ================== VERIFIER MODE ==================
if [[ "${1:-}" == "verify" ]]; then
  FILE="${2:-}"
  [[ -z "$FILE" ]] && echo "Usage: $0 verify <report_file>" && exit 1
  [[ ! -f "$FILE" ]] && echo "File not found." && exit 1

  echo -e "${CYAN}${BOLD}🕵️  VERIFIER MODE — $APP${RESET}\n"

  [[ ! -f "$KEYDIR/public.pem" ]] && echo "Missing public key." && exit 1
  [[ ! -f "$FILE.sha256" || ! -f "$FILE.sig" ]] && echo "Missing signature files." && exit 1

  sha256sum -c "$FILE.sha256" || exit 1
  openssl dgst -sha256 -verify "$KEYDIR/public.pem" -signature "$FILE.sig" "$FILE" || exit 1

  echo -e "\n${GREEN}${BOLD}[✔] VERIFIED — AUTHENTIC & UNMODIFIED${RESET}"
  exit 0
fi

TARGET="${1:-}"
[[ -z "$TARGET" ]] && echo "Usage: $0 https://example.com" && exit 1

if [[ ! "$TARGET" =~ ^https?:// ]]; then
  echo "Error: target must start with http:// or https://"
  exit 1
fi

init_keys() {
  mkdir -p "$KEYDIR"
  if [[ ! -f "$KEYDIR/private.pem" ]]; then
    openssl genpkey -algorithm RSA -out "$KEYDIR/private.pem" -pkeyopt rsa_keygen_bits:2048 >/dev/null 2>&1
    openssl rsa -pubout -in "$KEYDIR/private.pem" -out "$KEYDIR/public.pem" >/dev/null 2>&1
  fi
}

sign_file() {
  sha256sum "$1" > "$1.sha256"
  openssl dgst -sha256 -sign "$KEYDIR/private.pem" -out "$1.sig" "$1"
}

ROWS=$(tput lines 2>/dev/null || echo 24)
COLS=$(tput cols 2>/dev/null || echo 80)

matrix_rain() {
  while true; do
    tput cup "$((RANDOM % ROWS))" "$((RANDOM % COLS))" 2>/dev/null || true
    printf "${GREEN}%s${RESET}" "$(printf "\\$(printf '%03o' $((RANDOM % 94 + 33)))")"
    sleep 0.03
  done
}

draw_frame() {
  clear
  echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${RESET}"
  printf "${GREEN}║ %-52s ║${RESET}\n" "$APP"
  printf "${GREEN}║ TARGET: %-44s ║${RESET}\n" "$TARGET"
  echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${RESET}"
  echo -e "${BLUE}║ [1] Headers [2] TLS [3] CORS [4] Methods [5] Cache   ║${RESET}"
  echo -e "${BLUE}║ [6] Charts  [7] Export  [8] AI Risk  [Q] Quit        ║${RESET}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${RESET}"
}

panel() {
  echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
  printf "${CYAN}║ %-52s ║${RESET}\n" "$1"
  echo -e "${CYAN}╠══════════════════════════════════════════════════════╣${RESET}"
}

panel_end() {
  echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
}

check_headers() {
  panel "Security Headers"
  out=$(curl -k -sS -I --max-time 10 "$TARGET" | grep -Ei "content-security-policy|x-frame-options|x-content-type-options|strict-transport-security" || true)
  [[ -n "$out" ]] && RESULTS[headers]=1 && echo "$out" || echo -e "${RED}Missing common security headers${RESET}"
  panel_end
  pause
}

check_tls() {
  panel "TLS / HTTPS"
  out=$(curl -k -sS -vI --https-only --max-time 10 "$TARGET" 2>&1 | grep -Ei "TLS|SSL" || true)
  [[ -n "$out" ]] && RESULTS[tls]=1 && echo "$out" || echo -e "${RED}No TLS detected${RESET}"
  panel_end
  pause
}

check_cors() {
  panel "CORS Policy"
  out=$(curl -k -sS -I --max-time 10 -H "Origin: https://evil.example" "$TARGET" | grep -i access-control || true)
  [[ -n "$out" ]] && RESULTS[cors]=1 && echo "$out" || echo -e "${DIM}No CORS headers${RESET}"
  panel_end
  pause
}

check_methods() {
  panel "HTTP Methods"
  out=$(curl -k -sS -X OPTIONS -i --max-time 10 "$TARGET" | grep -i allow || true)
  [[ -n "$out" ]] && RESULTS[methods]=1 && echo "$out" || echo -e "${DIM}No Allow header${RESET}"
  panel_end
  pause
}

check_cache() {
  panel "Cache Control"
  out=$(curl -k -sS -I --max-time 10 "$TARGET" | grep -i cache-control || true)
  [[ -n "$out" ]] && RESULTS[cache]=1 && echo "$out" || echo -e "${DIM}No cache-control${RESET}"
  panel_end
  pause
}

draw_chart() {
  panel "Security Coverage Chart"
  for k in headers tls cors methods cache; do
    v="${RESULTS[$k]}"
    if [[ "$v" -eq 1 ]]; then
      bar="██████████"
      s="${GREEN}OK${RESET}"
    else
      bar=""
      s="${RED}MISS${RESET}"
    fi
    printf "%-10s [%-10s] %b\n" "$k" "$bar" "$s"
  done
  panel_end
  pause
}

ai_risk() {
  panel "🧠 AI Risk Interpretation"
  score=0

  [[ ${RESULTS[headers]} -eq 0 ]] && echo "[-] Missing headers → XSS / Clickjacking" && ((score+=2))
  [[ ${RESULTS[tls]} -eq 0 ]] && echo "[-] No TLS → MITM risk" && ((score+=3))
  [[ ${RESULTS[cors]} -eq 0 ]] && echo "[!] No explicit CORS policy" && ((score+=1))
  [[ ${RESULTS[methods]} -eq 0 ]] && echo "[-] Methods unrestricted or unknown" && ((score+=2))
  [[ ${RESULTS[cache]} -eq 0 ]] && echo "[!] Cache not controlled" && ((score+=1))

  echo
  if (( score <= 2 )); then
    echo -e "${GREEN}${BOLD}Overall Risk: LOW${RESET}"
  elif (( score <= 5 )); then
    echo -e "${BLUE}${BOLD}Overall Risk: MEDIUM${RESET}"
  else
    echo -e "${RED}${BOLD}Overall Risk: HIGH${RESET}"
  fi

  panel_end
}

export_reports() {
  TS=$(date +%Y%m%d_%H%M%S)
  init_keys

  JSON="report_$TS.json"
  HTML="report_$TS.html"
  AI="ai_$TS.txt"

  cat > "$JSON" <<EOF
{
  "target": "$TARGET",
  "timestamp": "$TS",
  "results": {
    "headers": ${RESULTS[headers]},
    "tls": ${RESULTS[tls]},
    "cors": ${RESULTS[cors]},
    "methods": ${RESULTS[methods]},
    "cache": ${RESULTS[cache]}
  }
}
EOF

  cat > "$HTML" <<EOF
<html>
<body style="background:black;color:#00ff88;font-family:monospace">
<h1>$APP</h1>
<p><b>Target:</b> $TARGET</p>
<pre>$(cat "$JSON")</pre>
</body>
</html>
EOF

  ai_risk > "$AI"

  sign_file "$JSON"
  sign_file "$HTML"
  sign_file "$AI"

  panel "Reports Exported & Signed"
  echo "$JSON / $HTML / $AI"
  echo "Public key: $KEYDIR/public.pem"
  panel_end
  pause
}

tput civis 2>/dev/null || true
matrix_rain &
RAIN_PID=$!

while true; do
  draw_frame
  read -rsn1 key
  case "$key" in
    1) check_headers ;;
    2) check_tls ;;
    3) check_cors ;;
    4) check_methods ;;
    5) check_cache ;;
    6) draw_chart ;;
    7) export_reports ;;
    8) ai_risk; pause ;;
    q|Q) exit 0 ;;
  esac
done
