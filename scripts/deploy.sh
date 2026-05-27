#!/usr/bin/env bash
# FreeAssist — Fly.io deployment script
# Usage: ./scripts/deploy.sh [api|web|all]
set -euo pipefail

TARGET="${1:-all}"

deploy_api() {
  echo "→ Deploying freeassist-api to Fly.io (Paris/cdg)..."
  cd apps/api
  fly deploy --app freeassist-api --region cdg
  cd ../..
}

deploy_web() {
  echo "→ Deploying freeassist-web to Fly.io (Paris/cdg)..."
  cd apps/web
  fly deploy --app freeassist-web --region cdg
  cd ../..
}

setup_secrets() {
  echo "→ Setting Fly.io secrets for freeassist-api..."
  fly secrets set \
    DATABASE_URL="$DATABASE_URL" \
    REDIS_URL="$REDIS_URL" \
    SECRET_KEY="$SECRET_KEY" \
    --app freeassist-api
}

case "$TARGET" in
  api)   deploy_api ;;
  web)   deploy_web ;;
  all)   deploy_api && deploy_web ;;
  secrets) setup_secrets ;;
  *)
    echo "Usage: $0 [api|web|all|secrets]"
    exit 1
    ;;
esac

echo "✓ Deployment complete"
