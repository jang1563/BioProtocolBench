# Release Checklist

Use this checklist before tagging or announcing a public BioProtocolBench
snapshot.

## Scope and naming

- Keep the public benchmark name as BioProtocolBench and the v0.1.x installable
  distribution name as `labcraft`.
- Treat direct `src.*` imports as internal compatibility paths for v0.1.x.
  Avoid introducing a second public import namespace in a patch release.
- Keep multi-task execution on [scripts/run_portfolio_eval.sh](../scripts/run_portfolio_eval.sh)
  presets: `snapshot`, `current`, `discovery`, and `all`.
- Keep `labcraft_suite()` as a single-task smoke alias unless a future breaking
  release introduces a real cross-task Inspect orchestration layer.

## Required checks

```bash
uv run pytest
uv run pytest tests/test_citations.py tests/test_scope_compliance.py tests/test_inspect_task.py
```

## Metadata checks

- Confirm [CITATION.cff](../CITATION.cff) has the intended version and release
  date.
- Confirm [README.md](../README.md), [NOTICE](../NOTICE), [LICENSE](../LICENSE),
  and [LICENSE-DATA](../LICENSE-DATA) describe the same licensing split.
- Confirm [pyproject.toml](../pyproject.toml) metadata points to the current
  repository and issue tracker.
- Include the commit SHA and log/result directory when reporting benchmark
  numbers.

## Result bundle checks

- Frozen snapshot results should stay tied to `results/logs`,
  `results/results.md`, and the top-level scorecard plots.
- Newer wet-lab task bundles should remain in their `results/current_*`
  directories unless intentionally promoted.
- Discovery Decision Track bundles should remain in `results/discovery_*`.
- Do not overwrite existing `.eval` logs when extending a seed range; use
  `SEED_START` and a separate `LOG_DIR` when needed.
