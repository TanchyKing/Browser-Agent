from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import pytest

import scripts.blind.evaluator_only as evaluator
from scripts.blind.sealed_bundle import unprotect


@pytest.mark.skipif(os.name != "nt", reason="Blind artifacts use Windows DPAPI")
def test_mock_run_path_seals_unscored_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "runtime"
    entropy = os.urandom(32)
    task_id = "blind_mock_task"
    task_bundle = {
        "tasks": [
            {
                "task_id": task_id,
                "family": "jobs",
                "page_file": "page.html",
                "task": {
                    "task_id": task_id,
                    "instruction": "Complete the sealed mock browser task.",
                    "allowed_actions": ["finish"],
                    "forbidden_actions": [],
                    "agent_contract": {"required_slots": {}},
                    "success_check": {
                        "mode": "scripted_dom",
                        "all_of": [
                            {
                                "kind": "element_text",
                                "target": "#result",
                                "value": "__SEALED_EXPECTATION__",
                            }
                        ],
                    },
                },
            }
        ],
        "pages": {
            "page.html": base64.b64encode(
                b"<!doctype html><html><body><p id=result>mock</p></body></html>"
            ).decode("ascii")
        },
    }
    prereg = {
        "comparison_points": {
            "R10g_base": {
                "model_name": "qwen3:8b",
                "model_digest": "a" * 64,
            }
        }
    }
    receipt = {"suite_sha256": "b" * 64, "manifest_sha256": "c" * 64}

    monkeypatch.setattr(evaluator, "RUNTIME_ROOT", runtime)
    monkeypatch.setattr(evaluator, "FINAL_SCORE_PATH", tmp_path / "score.json")
    monkeypatch.setattr(evaluator, "UNSEAL_RECEIPT_PATH", tmp_path / "unseal.json")
    monkeypatch.setattr(
        evaluator, "_external_unseal_marker", lambda: tmp_path / "external-unseal.json"
    )
    monkeypatch.setattr(
        evaluator, "_assert_public_hashes", lambda: ({}, receipt, prereg)
    )
    monkeypatch.setattr(evaluator, "_assert_frozen_files", lambda _: None)
    monkeypatch.setattr(evaluator, "load_entropy", lambda: entropy)
    monkeypatch.setattr(
        evaluator, "_verify_task_bundle_only", lambda *_: task_bundle
    )
    monkeypatch.setattr(evaluator, "_ollama_model_digest", lambda _: "a" * 64)

    def fake_run_demo(task_id_arg, trace_out, run_out, *, backend, config):
        assert task_id_arg == task_id
        assert backend == "ollama"
        assert config.inference.model_name == "qwen3:8b"
        return {
            "task_id": task_id,
            "status": "success",
            "errors": [],
            "terminal_action": "finish",
            "steps": [],
            "final_state": {"elements": {"#result": {"exists": True, "text": "mock"}}},
            "experiment": {"sha256": "d" * 64, "source_path": "temporary"},
            "artifacts": {"browser_trace": str(trace_out)},
        }

    monkeypatch.setattr(evaluator, "run_demo", fake_run_demo)
    assert evaluator.command_run("R10g_base", "qwen3:8b") == 0

    ciphertext = (runtime / "R10g_base.runs.dpapi").read_bytes()
    sealed = json.loads(unprotect(ciphertext, entropy).decode("utf-8"))
    assert sealed["run_count"] == 1
    assert sealed["runs"][0]["score_state"] == "sealed_pending_two_model_unseal"
    assert "status" not in sealed["runs"][0]
    assert "errors" not in sealed["runs"][0]
    public_receipt = json.loads(
        (runtime / "R10g_base.receipt.json").read_text(encoding="utf-8")
    )
    assert public_receipt["scores_visible"] is False


def test_aggregate_reports_only_counts_and_rates() -> None:
    task_id = "blind_mock_business"
    sealed = {
        "model_name": "mock",
        "model_digest": "f" * 64,
        "runs": [
            {
                "task_id": task_id,
                "terminal_action": "finish",
                "final_state": {
                    "elements": {"#result": {"exists": True, "text": "done"}}
                },
                "steps": [],
            }
        ],
    }
    expectations = {
        task_id: {
            "family": "jobs",
            "success_check_v2": {
                "mode": "scripted_dom",
                "all_of": [
                    {"kind": "element_text", "target": "#result", "value": "done"}
                ],
            },
        }
    }
    result = evaluator._aggregate_one("R10g_base", sealed, expectations)
    assert result["business"] == {"passed": 1, "total": 1, "task_success_rate": 1.0}
    assert result["overall"]["success_count"] == 1
    assert "runs" not in result
