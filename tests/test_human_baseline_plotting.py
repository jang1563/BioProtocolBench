import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(module_name: str, relative_path: str):
    script_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


plot_human_baseline = _load_script_module(
    "plot_human_baseline",
    "scripts/plot_human_baseline.py",
)


def test_plot_human_baseline_writes_pngs(tmp_path):
    report_path = tmp_path / "human_baseline_pilot.json"
    out_dir = tmp_path / "plots"
    report_path.write_text(
        json.dumps(
            {
                "coverage": [
                    {
                        "task_id": "transform_01",
                        "seed_index": 0,
                        "human_sessions": 1,
                        "operators": "expert_a",
                        "snapshot_range_display": "0.400-0.800",
                        "snapshot_scores_by_model": {
                            "gpt-4o-mini": 0.6,
                            "gpt-4o": 0.45,
                            "claude-haiku-4-5": 0.4,
                            "claude-sonnet-4-5": 0.8,
                        },
                    },
                    {
                        "task_id": "growth_01",
                        "seed_index": 3,
                        "human_sessions": 0,
                        "operators": "-",
                        "snapshot_range_display": "0.200-1.000",
                        "snapshot_scores_by_model": {
                            "gpt-4o-mini": 0.7,
                            "gpt-4o": 0.2,
                            "claude-haiku-4-5": 1.0,
                            "claude-sonnet-4-5": 1.0,
                        },
                    },
                ],
                "sessions": [
                    {
                        "task_id": "transform_01",
                        "seed_index": 0,
                        "overall": 0.92,
                    }
                ],
            }
        )
    )

    rc = plot_human_baseline.main(
        ["--report", str(report_path), "--out-dir", str(out_dir)]
    )

    assert rc == 0
    assert (out_dir / "coverage.png").exists()
    assert (out_dir / "seed_context.png").exists()
