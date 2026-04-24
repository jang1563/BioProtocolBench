#!/usr/bin/env bash
# Convenience wrapper for the recommended discovery-decision bundle.
#
# Runs the discovery preset through the portfolio runner, then regenerates the
# aggregate markdown table and plots in their default discovery locations.
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

RUNNER_SCRIPT="${RUNNER_SCRIPT:-${REPO_ROOT}/scripts/run_portfolio_eval.sh}"
AGGREGATE_SCRIPT="${AGGREGATE_SCRIPT:-${REPO_ROOT}/scripts/aggregate_eval_results.py}"
PLOT_SCRIPT="${PLOT_SCRIPT:-${REPO_ROOT}/scripts/plot_scorecard.py}"

: "${MODELS:=openai/gpt-4o-mini anthropic/claude-sonnet-4-5}"
: "${SEEDS:=3}"
: "${SEED_START:=0}"
: "${LOG_DIR:=${REPO_ROOT}/results/discovery_logs}"
: "${RESULTS_OUT:=${REPO_ROOT}/results/discovery_track_results.md}"
: "${PLOTS_OUT_DIR:=${REPO_ROOT}/results/discovery_track_plots}"

TASK_PRESET="discovery"

run_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    "${PYTHON_BIN}" "$@"
    return
  fi
  if [ -x "${REPO_ROOT}/.venv/bin/python" ]; then
    "${REPO_ROOT}/.venv/bin/python" "$@"
    return
  fi
  if command -v uv >/dev/null 2>&1; then
    uv run python "$@"
    return
  fi
  python3 "$@"
}

mkdir -p "${LOG_DIR}" "$(dirname "${RESULTS_OUT}")" "${PLOTS_OUT_DIR}"

echo "Running Discovery decision bundle"
echo "  Models: ${MODELS}"
echo "  Seeds: ${SEEDS}"
echo "  Seed start: ${SEED_START}"
echo "  Logs: ${LOG_DIR}"
echo "  Results: ${RESULTS_OUT}"
echo "  Plots: ${PLOTS_OUT_DIR}"
echo

TASK_PRESET="${TASK_PRESET}" \
LOG_DIR="${LOG_DIR}" \
MODELS="${MODELS}" \
SEEDS="${SEEDS}" \
SEED_START="${SEED_START}" \
  bash "${RUNNER_SCRIPT}"

run_python "${AGGREGATE_SCRIPT}" \
  --log-dir "${LOG_DIR}" \
  --out "${RESULTS_OUT}"

plot_models=()
for model in ${MODELS}; do
  plot_models+=("${model}")
done

run_python "${PLOT_SCRIPT}" \
  --log-dir "${LOG_DIR}" \
  --out-dir "${PLOTS_OUT_DIR}" \
  --task-preset discovery \
  --models "${plot_models[@]}"

echo
echo "Discovery bundle complete."
