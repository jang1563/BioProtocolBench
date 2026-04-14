#!/usr/bin/env bash
# Portfolio evaluation runner: tasks x models x seeds
#
# Runs each LabCraft task across the configured model list using the
# `seeds` task parameter to expand into N stochastic samples per task.
#
# Usage:
#   ./scripts/run_portfolio_eval.sh               # run all tasks x all models
#   SEEDS=5 ./scripts/run_portfolio_eval.sh       # 5 seeds per task per model
#   MODELS="openai/gpt-4o-mini" ./scripts/run_portfolio_eval.sh
#   TASKS="transform_01 clone_01" ./scripts/run_portfolio_eval.sh
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO_ROOT"

: "${SEEDS:=3}"
: "${TASKS:=transform_01 growth_01 pcr_01 screen_01 clone_01}"
: "${MODELS:=openai/gpt-4o-mini openai/gpt-4o anthropic/claude-haiku-4-5}"
: "${LOG_DIR:=${REPO_ROOT}/results/logs}"

# Pull API keys from the user's standard dotfile (ANTHROPIC_API_KEY, OPENAI_API_KEY).
if [ -f "$HOME/.api_keys" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.api_keys" >/dev/null 2>&1
fi

export HOME=/tmp/inspect_ai_home
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CACHE_HOME="$HOME/.cache"
mkdir -p "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$LOG_DIR"

INSPECT_BIN=${INSPECT_BIN:-/tmp/labcraft-py311/bin/inspect}
if [ ! -x "$INSPECT_BIN" ]; then
  INSPECT_BIN=inspect
fi

echo "Running portfolio eval"
echo "  Tasks:  $TASKS"
echo "  Models: $MODELS"
echo "  Seeds:  $SEEDS"
echo "  Logs:   $LOG_DIR"
echo

for task in $TASKS; do
  for model in $MODELS; do
    echo "=== task=$task model=$model seeds=$SEEDS ==="
    "$INSPECT_BIN" eval "src/inspect_task.py@${task}" \
      --model "$model" \
      -T "seeds=${SEEDS}" \
      --log-dir "$LOG_DIR" \
      || echo "!! run failed: task=$task model=$model"
  done
done

echo
echo "All runs attempted. Aggregate with:"
echo "  python3 scripts/aggregate_eval_results.py"
