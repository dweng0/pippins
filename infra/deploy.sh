#!/bin/bash
# Pull-based deploy: runs on the EC2 box from a systemd timer. Deploys origin/main only if
# CI (ci.yml) concluded "success" for that exact commit. No inbound SSH needed.
set -euo pipefail

REPO="dweng0/stackcx-assessment"
cd /home/ec2-user/app

git fetch -q origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
[ "$LOCAL" = "$REMOTE" ] && exit 0

CONCLUSION=$(curl -sf "https://api.github.com/repos/${REPO}/actions/workflows/ci.yml/runs?head_sha=${REMOTE}&status=completed" \
  | python3 -c 'import sys,json; r=json.load(sys.stdin)["workflow_runs"]; print(r[0]["conclusion"] if r else "none")')

if [ "$CONCLUSION" != "success" ]; then
  echo "CI is '${CONCLUSION}' for ${REMOTE}, not deploying"
  exit 0
fi

echo "Deploying ${REMOTE}"
git merge --ff-only origin/main
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
