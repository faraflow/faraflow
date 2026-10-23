# Copyright 2026 Alokin LLC
# SPDX-License-Identifier: FCL-1.0-ALv2
"""End-to-end tests for run / rerun / continue semantics.

Uses a linear workflow input_node -> double -> plus_one built from deterministic
PythonFuncNodes. Each function node appends one byte to a counter file when it
actually executes, so tests can assert exactly which nodes ran.

Starlette's TestClient executes FastAPI BackgroundTasks synchronously before the
POST returns, so /start_run/ and /run_partial/ are already finished when the
next line of a test runs — no polling needed.
"""

from pathlib import Path
from typing import Any, Dict, Optional

FAIL_CODE = "raise RuntimeError('boom')"


def counted(counter: Path, code: str) -> str:
    """Prefix node code with a side-effect that records one execution."""
    return f"with open(r'{counter}', 'a') as f:\n    f.write('x')\n{code}"


def executions(counter: Path) -> int:
    return len(counter.read_text()) if counter.exists() else 0


def make_definition(double_code: str, plus_one_code: str) -> Dict[str, Any]:
    return {
        "nodes": [
            {
                "id": "input_node",
                "title": "input_node",
                "node_type": "InputNode",
                "config": {"output_schema": {"x": "int"}},
                "coordinates": {"x": 0, "y": 0},
            },
            {
                "id": "double",
                "title": "double",
                "node_type": "PythonFuncNode",
                "config": {"code": double_code, "output_schema": {"value": "int"}},
                "coordinates": {"x": 200, "y": 0},
            },
            {
                "id": "plus_one",
                "title": "plus_one",
                "node_type": "PythonFuncNode",
                "config": {"code": plus_one_code, "output_schema": {"value": "int"}},
                "coordinates": {"x": 400, "y": 0},
            },
        ],
        "links": [
            {"source_id": "input_node", "target_id": "double"},
            {"source_id": "double", "target_id": "plus_one"},
        ],
    }


INITIAL_INPUTS = {"initial_inputs": {"input_node": {"x": 21}}}


def create_workflow(client, definition: Dict[str, Any]) -> str:
    resp = client.post("/wf/", json={"name": "t", "description": "", "definition": definition})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def update_workflow(client, workflow_id: str, definition: Dict[str, Any]) -> None:
    resp = client.put(
        f"/wf/{workflow_id}/",
        json={"name": "t", "description": "", "definition": definition},
    )
    assert resp.status_code == 200, resp.text


def start_run(client, workflow_id: str, parent_run_id: Optional[str] = None) -> Dict[str, Any]:
    resp = client.post(
        f"/wf/{workflow_id}/start_run/",
        json={**INITIAL_INPUTS, "parent_run_id": parent_run_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def continue_run(
    client,
    workflow_id: str,
    original_run_id: str,
    continue_from_node_id: Optional[str] = None,
):
    return client.post(
        f"/wf/{workflow_id}/run_partial/",
        json={
            **INITIAL_INPUTS,
            "original_run_id": original_run_id,
            "continue_from_node_id": continue_from_node_id,
        },
    )


def run_status(client, run_id: str) -> Dict[str, Any]:
    resp = client.get(f"/run/{run_id}/status/")
    assert resp.status_code == 200, resp.text
    return resp.json()


def tasks_by_node(status: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {t["node_id"]: t for t in status["tasks"]}


def good_codes(tmp_path: Path, double_delta: str = "* 2"):
    """Counter files + working code for both function nodes."""
    double_counter = tmp_path / "double.count"
    plus_one_counter = tmp_path / "plus_one.count"
    double_code = counted(double_counter, f"return {{'value': input_model.input_node.x {double_delta}}}")
    plus_one_code = counted(plus_one_counter, "return {'value': input_model.double.value + 1}")
    return double_counter, plus_one_counter, double_code, plus_one_code


def test_continue_of_failed_run(client, tmp_path):
    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    # 1. Run with a failing 'double' node — run ends FAILED, downstream canceled.
    wf_id = create_workflow(client, make_definition(FAIL_CODE, plus_one_code))
    run = start_run(client, wf_id)
    orig = run_status(client, run["id"])
    assert orig["status"] == "FAILED"
    orig_tasks = tasks_by_node(orig)
    assert orig_tasks["double"]["status"] == "FAILED"
    assert orig_tasks["plus_one"]["status"] == "CANCELED"
    assert executions(plus_one_counter) == 0

    # 2. Fix the workflow, then auto-continue.
    update_workflow(client, wf_id, make_definition(double_code, plus_one_code))
    cont = continue_run(client, wf_id, run["id"]).json()
    cont_status = run_status(client, cont["id"])

    assert cont_status["status"] == "COMPLETED"
    assert cont_status["parent_run_id"] == run["id"]

    cont_tasks = tasks_by_node(cont_status)
    # Cached node: task row copied verbatim from the original run — identical
    # start_time proves it was not re-executed.
    assert cont_tasks["input_node"]["start_time"] == orig_tasks["input_node"]["start_time"]
    # Previously failed / canceled nodes re-ran and succeeded.
    assert cont_tasks["double"]["status"] == "COMPLETED"
    assert cont_tasks["plus_one"]["outputs"]["value"] == 43
    assert executions(double_counter) == 1
    assert executions(plus_one_counter) == 1

    # 3. No merge-back: the original run's history is untouched.
    orig_after = run_status(client, run["id"])
    assert orig_after["status"] == "FAILED"
    assert {n: t["status"] for n, t in tasks_by_node(orig_after).items()} == {
        n: t["status"] for n, t in orig_tasks.items()
    }


def test_continue_chaining(client, tmp_path):
    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    # Run 1: double fails.
    wf_id = create_workflow(client, make_definition(FAIL_CODE, FAIL_CODE))
    run1 = start_run(client, wf_id)
    assert run_status(client, run1["id"])["status"] == "FAILED"

    # Continue 1: double fixed, plus_one still fails.
    update_workflow(client, wf_id, make_definition(double_code, FAIL_CODE))
    cont1 = continue_run(client, wf_id, run1["id"]).json()
    cont1_status = run_status(client, cont1["id"])
    assert cont1_status["status"] == "FAILED"
    assert tasks_by_node(cont1_status)["double"]["status"] == "COMPLETED"
    assert executions(double_counter) == 1

    # Continue 2 targets the *continue* run — its own completed work is the cache.
    update_workflow(client, wf_id, make_definition(double_code, plus_one_code))
    cont2 = continue_run(client, wf_id, cont1["id"]).json()
    cont2_status = run_status(client, cont2["id"])
    assert cont2_status["status"] == "COMPLETED"
    assert cont2_status["parent_run_id"] == cont1["id"]
    cont2_tasks = tasks_by_node(cont2_status)
    # double was cached from cont1 (copied row), not re-executed.
    assert cont2_tasks["double"]["start_time"] == tasks_by_node(cont1_status)["double"]["start_time"]
    assert executions(double_counter) == 1
    assert cont2_tasks["plus_one"]["outputs"]["value"] == 43

    # Both ancestors keep their own history.
    assert run_status(client, run1["id"])["status"] == "FAILED"
    assert run_status(client, cont1["id"])["status"] == "FAILED"


def test_continue_of_canceled_run(client, tmp_path):
    from pyspur.database import SessionLocal
    from pyspur.models.run_model import RunModel, RunStatus
    from pyspur.models.task_model import TaskModel, TaskStatus

    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    # Produce a FAILED run, then rewrite it as CANCELED (TestClient runs
    # background tasks synchronously, so a genuine mid-run cancel isn't possible).
    wf_id = create_workflow(client, make_definition(FAIL_CODE, plus_one_code))
    run = start_run(client, wf_id)
    with SessionLocal() as session:
        run_row = session.query(RunModel).filter(RunModel.id == run["id"]).one()
        run_row.status = RunStatus.CANCELED
        for task in session.query(TaskModel).filter(TaskModel.run_id == run["id"]).all():
            if task.status != TaskStatus.COMPLETED:
                task.status = TaskStatus.CANCELED
        session.commit()
    assert run_status(client, run["id"])["status"] == "CANCELED"

    # Continue re-executes only the non-completed nodes.
    update_workflow(client, wf_id, make_definition(double_code, plus_one_code))
    cont = continue_run(client, wf_id, run["id"]).json()
    cont_status = run_status(client, cont["id"])
    assert cont_status["status"] == "COMPLETED"
    assert tasks_by_node(cont_status)["plus_one"]["outputs"]["value"] == 43
    assert executions(double_counter) == 1
    # Original stays CANCELED.
    assert run_status(client, run["id"])["status"] == "CANCELED"


def test_rerun_reexecutes_everything(client, tmp_path):
    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    wf_id = create_workflow(client, make_definition(double_code, plus_one_code))
    run1 = start_run(client, wf_id)
    assert run_status(client, run1["id"])["status"] == "COMPLETED"
    assert executions(double_counter) == 1
    assert executions(plus_one_counter) == 1

    # Rerun: parent_run_id is lineage only — everything executes again.
    run2 = start_run(client, wf_id, parent_run_id=run1["id"])
    run2_status = run_status(client, run2["id"])
    assert run2_status["status"] == "COMPLETED"
    assert run2_status["parent_run_id"] == run1["id"]
    assert executions(double_counter) == 2
    assert executions(plus_one_counter) == 2


def test_continue_from_node_reruns_subtree(client, tmp_path):
    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    wf_id = create_workflow(client, make_definition(double_code, plus_one_code))
    run = start_run(client, wf_id)
    orig = run_status(client, run["id"])
    assert orig["status"] == "COMPLETED"

    # Change double's logic so its output diverges — the whole subtree re-runs.
    _, _, changed_double_code, _ = good_codes(tmp_path, double_delta="* 3")
    update_workflow(client, wf_id, make_definition(changed_double_code, plus_one_code))

    cont = continue_run(client, wf_id, run["id"], continue_from_node_id="double").json()
    cont_status = run_status(client, cont["id"])
    assert cont_status["status"] == "COMPLETED"
    cont_tasks = tasks_by_node(cont_status)
    # input_node cached (copied row), forced node + diverged descendant re-ran.
    assert cont_tasks["input_node"]["start_time"] == tasks_by_node(orig)["input_node"]["start_time"]
    assert cont_tasks["double"]["outputs"]["value"] == 63
    assert cont_tasks["plus_one"]["outputs"]["value"] == 64
    assert executions(double_counter) == 2
    assert executions(plus_one_counter) == 2


def test_continue_from_node_output_cutoff(client, tmp_path):
    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    wf_id = create_workflow(client, make_definition(double_code, plus_one_code))
    run = start_run(client, wf_id)
    assert run_status(client, run["id"])["status"] == "COMPLETED"
    assert executions(double_counter) == 1
    assert executions(plus_one_counter) == 1

    # Force-rerun 'double': it ALWAYS executes; its fresh output is identical to
    # the original run's recorded output, so descendants are cut off and reuse
    # their original outputs.
    cont = continue_run(client, wf_id, run["id"], continue_from_node_id="double").json()
    cont_status = run_status(client, cont["id"])
    assert cont_status["status"] == "COMPLETED"
    cont_tasks = tasks_by_node(cont_status)
    assert cont_tasks["double"]["status"] == "COMPLETED"
    assert cont_tasks["plus_one"]["status"] == "COMPLETED"
    assert cont_tasks["plus_one"]["outputs"]["value"] == 43
    assert executions(double_counter) == 2  # forced node re-executed
    assert executions(plus_one_counter) == 1  # descendant reused — output unchanged


def test_continue_from_node_always_executes_despite_config_change(client, tmp_path):
    """The forced node re-executes even when its config changed; the cutoff
    decision is made on its OUTPUT, not its inputs or config."""
    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    wf_id = create_workflow(client, make_definition(double_code, plus_one_code))
    run = start_run(client, wf_id)
    assert run_status(client, run["id"])["status"] == "COMPLETED"

    # Cosmetic config change: different code text, same result.
    cosmetic_double_code = f"# tweaked but equivalent\n{double_code}"
    update_workflow(client, wf_id, make_definition(cosmetic_double_code, plus_one_code))

    cont = continue_run(client, wf_id, run["id"], continue_from_node_id="double").json()
    cont_status = run_status(client, cont["id"])
    assert cont_status["status"] == "COMPLETED"
    assert tasks_by_node(cont_status)["plus_one"]["outputs"]["value"] == 43
    assert executions(double_counter) == 2  # re-executed with the new config
    assert executions(plus_one_counter) == 1  # output identical → descendant cut off


def test_continue_from_node_descendant_config_change_reexecutes(client, tmp_path):
    """A -> B -> C, re-execute B: even when B's output is identical to the
    original run, a config change on C forces C to re-execute."""
    double_counter, plus_one_counter, double_code, plus_one_code = good_codes(tmp_path)

    wf_id = create_workflow(client, make_definition(double_code, plus_one_code))
    run = start_run(client, wf_id)
    assert run_status(client, run["id"])["status"] == "COMPLETED"
    assert executions(plus_one_counter) == 1

    # Change C's (plus_one's) config: now adds 2 instead of 1.
    changed_plus_one_code = counted(
        plus_one_counter, "return {'value': input_model.double.value + 2}"
    )
    update_workflow(client, wf_id, make_definition(double_code, changed_plus_one_code))

    # Re-execute B (double): its output is unchanged, but C's config changed.
    cont = continue_run(client, wf_id, run["id"], continue_from_node_id="double").json()
    cont_status = run_status(client, cont["id"])
    assert cont_status["status"] == "COMPLETED"
    cont_tasks = tasks_by_node(cont_status)
    assert cont_tasks["plus_one"]["outputs"]["value"] == 44  # new config took effect
    assert executions(double_counter) == 2  # B always re-executes
    assert executions(plus_one_counter) == 2  # C re-executed due to config change


def test_guard_completed_run(client, tmp_path):
    from pyspur.database import SessionLocal
    from pyspur.models.run_model import RunModel

    _, _, double_code, plus_one_code = good_codes(tmp_path)
    wf_id = create_workflow(client, make_definition(double_code, plus_one_code))
    run = start_run(client, wf_id)
    assert run_status(client, run["id"])["status"] == "COMPLETED"

    with SessionLocal() as session:
        runs_before = session.query(RunModel).count()

    resp = continue_run(client, wf_id, run["id"])
    assert resp.status_code == 400

    with SessionLocal() as session:
        assert session.query(RunModel).count() == runs_before
