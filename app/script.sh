#!/bin/bash
# script.sh — Initialize and start the Network Route Optimizer
# Usage: chmod +x script.sh && ./script.sh

set -e  # exit on any error

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "╔══════════════════════════════════════╗"
echo "║   Network Route Optimizer Setup      ║"
echo "╚══════════════════════════════════════╝"

# ── 1. Create .env if missing ──────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "→ Creating .env from .env.example..."
  cp .env.example .env
  echo "  ✓ .env created — edit DATABASE_URL if needed"
else
  echo "→ .env already exists — skipping"
fi

# ── 2. Create virtual environment ─────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "→ Creating virtual environment..."
  python3 -m venv .venv
  echo "  ✓ .venv created"
fi

source .venv/bin/activate

# ── 3. Install dependencies ────────────────────────────────────────────────────
echo "→ Installing dependencies..."
pip install -q --upgrade pip
pip install -q -e ".[dev]"
echo "  ✓ Dependencies installed"

# ── 4. Run Alembic migrations ─────────────────────────────────────────────────
echo "→ Running database migrations..."
alembic upgrade head
echo "  ✓ Migrations applied"

# ── 5. Start the server ────────────────────────────────────────────────────────
echo ""
echo "→ Starting server on http://localhost:8001"
echo "  Swagger docs: http://localhost:8001/docs"
echo "  Health check: http://localhost:8001/health"
echo ""
uvicorn app.network_optimizer.main:app --host 0.0.0.0 --port 8001 --reload
