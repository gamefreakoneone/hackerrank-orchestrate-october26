#!/usr/bin/env bash
# Copy this Claude Code session transcript into agent-trace/claude-code/, redacting likely secrets.
# Used as a Stop/SessionEnd hook (hook JSON on stdin). Never blocks: always exits 0.
input="$(cat 2>/dev/null)"
transcript="$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)"
session="$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)"
[ -n "$transcript" ] && [ -n "$session" ] && [ -f "$transcript" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
dest_dir="$root/agent-trace/claude-code"
mkdir -p "$dest_dir" 2>/dev/null || exit 0
dest="$dest_dir/$session.jsonl"
tmp="$dest.tmp.$$"

# Redacted values never include '\' or '"', so JSON string escapes stay intact (valid JSONL).
sed -E \
  -e 's/sk-[A-Za-z0-9_-]{20,}/[REDACTED]/g' \
  -e 's/AIza[0-9A-Za-z_-]{30,}/[REDACTED]/g' \
  -e 's/Bearer [A-Za-z0-9._-]{20,}/Bearer [REDACTED]/g' \
  -e 's/((API_KEY|SECRET|TOKEN)=)[^ "\\]+/\1[REDACTED]/g' \
  "$transcript" > "$tmp" 2>/dev/null && mv -f "$tmp" "$dest" 2>/dev/null
rm -f "$tmp" 2>/dev/null
exit 0
