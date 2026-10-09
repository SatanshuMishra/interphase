#!/usr/bin/env bash
set -euo pipefail

: > README.md

git init -q -b main
git config user.name fixture
git config user.email fixture@example.com
git add -A
git commit -q -m "Empty repository"
