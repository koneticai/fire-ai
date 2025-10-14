#!/bin/bash
set -euo pipefail
mkdir -p .cursor
if [ -d ".cursor/rules" ]; then
  mv .cursor/rules .cursor/_rules.off.$(date +%s)
  echo "Cursor rules disabled (renamed). Reopen Cursor to reduce indexing load."
else
  echo "No .cursor/rules folder; nothing to disable."
fi
