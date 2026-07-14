"""Run deterministic positive and fail-closed probes for reviewed IGD source refresh."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

import igd_refresh
from experimental_csharp_project import (
    PROPOSAL_STATUS,
    add_mapping_candidate,
    add_work_request,
    draft_change_proposal_from_mapping,
    validate_project_workspace,
)
from igd_daily import (
    ACCEPTED_REFRESH_PLAN_FILE,
    DailyLaunchError,
    digest_bytes,
    prepare_project,
    project_paths,
    project_status,
    read_json,
    validate_launch_record,
)
from igd_refresh import (
    PLAN_FILE,
    REFRESH_ACCEPT_AUTHORITY,
    REFRESH_AUTHORITY,
    REFRESH_DIRECTORY,
    REFRESH_PLAN_ROLE,
    REFRESH_PLAN_SCOPE,
    REFRESH_PLAN_STATUS,
    REFRESH_RECEIPT_ROLE,
    REVISIONS_DIRECTORY,
    accept_refresh,
    canonical_bytes,
    discard_refresh,
    plan_refresh,
    tree_digest,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "examples" / "product-smoke-csharp"
REPORT_ROLE = "intentgraph-local-source-refresh-negative-probes-report"
REPORT_STATUS = "intentgraph-local-source-refresh-negative-probes-passed"
RUNTIME_DIRECTORY = "intentgraph-p9.35-refresh-negative-probes"

RETAINED_WORK_ID = "refresh-retained-work"
STALE_WORK_ID = "refresh-stale-work"
PROPOSAL_ID = "refresh-stale-proposal"

PROBE_IDS = [
    "wrong-accept-plan-id",
    "wrong-discard-plan-id",
    "source-drift-after-plan",
    "active-workspace-drift",
    "candidate-workspace-drift",
    "status-candidate-workspace-drift",
    "pending-unexpected-entry",
    "plan-role-tamper",
    "plan-status-tamper",
    "plan-authority-tamper",
    "plan-revision-transition-tamper",
    "weakly-attributed-staged-revision-discard",
    "exact-staged-revision-with-extra-entry-discard",
    "revision-destination-collision",
    "launch-pointer-drift",
    "refresh-internal-reparse-point",
    "refresh-plan-file-reparse-point",
    "no-change-cleanup-pending-extra-entry",
    "no-change-cleanup-plan-file-reparse",
    "target-source-immutability",
    "injected-failure-before-launch-commit",
    "late-workspace-mutation-before-launch-commit",
    "injected-failure-after-launch-commit",
    "historical-revision-digest-tamper",
    "historical-revision-source-provenance-tamper",
    "active-revision-receipt-provenance-tamper",
    "receipt-authority-tamper",
    "receipt-structural-provenance-tamper",
    "receipt-joint-plan-digest-tamper",
    "accepted-plan-artifact-tamper",
    "coordinated-accepted-plan-provenance-tamper",
]


class HarnessError(RuntimeError):
    """Raised when a refresh invariant or expected failure is not observed."""


class InjectedCommitFailure(RuntimeError):
    """Raised only by the two atomic launch-pointer interruption probes."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HarnessError(message)


def exact_tree(root: Path) -> tuple[tuple[str, str, bytes], ...]:
    entries: list[tuple[str, str, bytes]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise HarnessError(f"unexpected symbolic link in harness tree: {relative}")
        if path.is_dir():
            entries.append(("directory", relative, b""))
        elif path.is_file():
            entries.append(("file", relative, path.read_bytes()))
    return tuple(entries)


def canonical_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def mutate_json(path: Path, mutation: Callable[[dict[str, Any]], None]) -> None:
    value = read_json(path)
    mutation(value)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def relative_workspace(project_root: Path, relative: str) -> Path:
    parsed = PurePosixPath(relative)
    require(
        not parsed.is_absolute() and parsed.parts and all(part not in {"", ".", ".."} for part in parsed.parts),
        "revision workspace path is not a safe relative path",
    )
    return project_root.joinpath(*parsed.parts)


def pending_contract(source: Path, home: Path) -> dict[str, Any]:
    paths = project_paths(source, home)
    launch = read_json(paths["launch"])
    launch_view = validate_launch_record(launch, source, paths["root"])
    plan_path = paths["root"] / REFRESH_DIRECTORY / "pending" / PLAN_FILE
    plan = read_json(plan_path)
    candidate = relative_workspace(paths["root"], plan["candidateWorkspace"])
    revision_destination = paths["root"] / REVISIONS_DIRECTORY / plan["toRevision"]["id"]
    return {
        "paths": paths,
        "launch": launch,
        "launchView": launch_view,
        "planPath": plan_path,
        "plan": plan,
        "candidate": candidate,
        "revisionDestination": revision_destination,
    }


def delta_counts(delta: dict[str, list[str]]) -> dict[str, int]:
    return {key: len(values) for key, values in sorted(delta.items())}


def run() -> dict[str, Any]:
    runtime_root = Path(tempfile.gettempdir()).resolve() / RUNTIME_DIRECTORY
    require(runtime_root.parent == Path(tempfile.gettempdir()).resolve(), "harness runtime root escaped the temporary directory")
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    runtime_root.mkdir()

    source_checks: list[dict[str, Any]] = []
    fixture_before = exact_tree(FIXTURE)

    def observe_source(operation_id: str, source: Path, operation: Callable[[], Any]) -> Any:
        before = exact_tree(source)
        before_digest = tree_digest(source)
        try:
            return operation()
        finally:
            after = exact_tree(source)
            after_digest = tree_digest(source)
            unchanged = before == after and before_digest == after_digest
            source_checks.append(
                {
                    "id": operation_id,
                    "beforeDigest": before_digest,
                    "afterDigest": after_digest,
                    "sourceBytesUnchanged": unchanged,
                }
            )
            require(unchanged, f"IGD operation mutated target source bytes: {operation_id}")

    try:
        source = runtime_root / "source"
        home = runtime_root / "positive-home"
        shutil.copytree(FIXTURE, source)
        refresh_target = source / "RefreshTarget.cs"
        refresh_target.write_bytes(
            b"namespace ProductSmoke;\n\n"
            b"public static class RefreshTarget\n"
            b"{\n"
            b"    public static int Value() => 1;\n"
            b"}\n"
        )
        initial_source_digest = tree_digest(source)

        prepared = observe_source(
            "prepare-r1",
            source,
            lambda: prepare_project(source, home, "P9.35 refresh probes"),
        )
        require(prepared["result"] == "pass" and prepared["action"] == "created", "initial prepare did not create r1")

        paths = project_paths(source, home)
        initial_launch = read_json(paths["launch"])
        initial_launch_view = validate_launch_record(initial_launch, source, paths["root"])
        r1_workspace = initial_launch_view["activeWorkspace"]
        r1_state, _, _, r1_data = validate_project_workspace(r1_workspace)
        facts = r1_data["facts"]["facts"]
        retained_fact = next(
            (
                fact
                for fact in facts
                if fact.get("kind") == "method" and fact.get("name") == "Add" and fact.get("sourceFile") == "Program.cs"
            ),
            None,
        )
        stale_fact = next(
            (
                fact
                for fact in facts
                if fact.get("kind") == "method"
                and fact.get("name") == "Value"
                and fact.get("sourceFile") == "RefreshTarget.cs"
            ),
            None,
        )
        require(retained_fact is not None and stale_fact is not None, "fixture methods were not extracted as code facts")

        observe_source(
            "add-retained-work-item",
            source,
            lambda: add_work_request(
                r1_workspace,
                RETAINED_WORK_ID,
                "Retain Program mapping",
                "Keep an unchanged Program.Add mapping across reviewed source refreshes.",
            ),
        )
        retained_mapping_result = observe_source(
            "add-retained-mapping",
            source,
            lambda: add_mapping_candidate(
                r1_workspace,
                RETAINED_WORK_ID,
                [retained_fact["id"]],
                "Program.cs is intentionally unchanged by both refreshes.",
            ),
        )
        observe_source(
            "add-stale-work-item",
            source,
            lambda: add_work_request(
                r1_workspace,
                STALE_WORK_ID,
                "Review changed method",
                "Track a method whose extracted fact becomes stale after an external source change.",
            ),
        )
        stale_mapping_result = observe_source(
            "add-stale-mapping",
            source,
            lambda: add_mapping_candidate(
                r1_workspace,
                STALE_WORK_ID,
                [stale_fact["id"]],
                "RefreshTarget.Value is the externally changed fact.",
            ),
        )
        proposal_result = observe_source(
            "draft-non-applied-proposal",
            source,
            lambda: draft_change_proposal_from_mapping(
                r1_workspace,
                proposal_id=PROPOSAL_ID,
                work_id=STALE_WORK_ID,
                title="Review RefreshTarget change",
                summary="Record review requirements without applying source changes.",
                verification_kind="local-review",
                verification_summary="Review the changed method against the new source snapshot.",
                evidence_kind="review-note",
                evidence_summary="Record a local review note without execution or approval claims.",
            ),
        )
        require(proposal_result["result"] == "pass", "non-applied proposal was not recorded")

        r1_state, _, _, r1_data = validate_project_workspace(r1_workspace)
        retained_mapping_id = retained_mapping_result["mappingId"]
        stale_mapping_id = stale_mapping_result["mappingId"]
        r1_proposal = next((item for item in r1_data["proposals"] if item["id"] == PROPOSAL_ID), None)
        require(r1_proposal is not None and r1_proposal["applicationStatus"] == PROPOSAL_STATUS, "proposal is not non-applied")
        sealed_r1_tree = exact_tree(r1_workspace)
        sealed_r1_digest = tree_digest(r1_workspace)

        first_source_before = refresh_target.read_bytes()
        require(first_source_before.count(b"=> 1;") == 1, "refresh target fixture does not contain the expected method")
        refresh_target.write_bytes(first_source_before.replace(b"=> 1;", b"=> checked(1 + 1);"))
        first_changed_source = exact_tree(source)
        first_changed_source_digest = tree_digest(source)

        launch_before_plan = paths["launch"].read_bytes()
        r1_before_plan = exact_tree(r1_workspace)
        plan_result = observe_source("plan-r1-to-r2", source, lambda: plan_refresh(source, home))
        require(plan_result["result"] == "review-required" and plan_result["action"] == "planned", "first refresh was not planned")
        require(paths["launch"].read_bytes() == launch_before_plan, "planning changed the launch pointer")
        require(exact_tree(r1_workspace) == r1_before_plan, "planning changed the active r1 workspace")
        require(exact_tree(source) == first_changed_source, "planning changed source bytes")

        pending = pending_contract(source, home)
        plan = pending["plan"]
        candidate = pending["candidate"]
        candidate_state, _, _, candidate_data = validate_project_workspace(candidate)
        plan_bytes = pending["planPath"].read_bytes()
        plan_digest = digest_bytes(canonical_bytes(plan))
        candidate_tree_before_repeat = exact_tree(candidate)
        candidate_digest = tree_digest(candidate)
        require(plan["artifactRole"] == REFRESH_PLAN_ROLE, "first plan role is invalid")
        require(plan["status"] == REFRESH_PLAN_STATUS and plan["scope"] == REFRESH_PLAN_SCOPE, "first plan status or scope is invalid")
        require(plan["fromRevision"]["id"] == "revision.r0001" and plan["toRevision"]["id"] == "revision.r0002", "first revision transition is invalid")
        require(plan["sourceDelta"]["changedPaths"] == ["RefreshTarget.cs"], "first source delta did not isolate RefreshTarget.cs")
        require(any(plan["codeFactDelta"].values()), "first plan has no code-fact delta")
        require(any(plan["relationDelta"].values()), "first plan has no relation delta")
        require(plan["invalidation"]["retainedMappingIds"] == [retained_mapping_id], "unchanged mapping was not retained")
        require(plan["invalidation"]["staleMappingIds"] == [stale_mapping_id], "changed mapping was not marked stale")
        require(plan["invalidation"]["staleProposalIds"] == [PROPOSAL_ID], "proposal was not marked stale")
        require([item["id"] for item in candidate_state["mappings"]] == [retained_mapping_id], "candidate mapping state does not match invalidation")
        require(not candidate_state["changeProposals"] and not candidate_data["proposals"], "candidate retained a snapshot-bound proposal")

        status_during_review = observe_source("status-review-required-r2", source, lambda: project_status(source, home))
        require(
            status_during_review["result"] == "refresh-review-required"
            and status_during_review["pendingRefreshPlanId"] == plan["id"]
            and status_during_review["activeRevision"] == "revision.r0001",
            "status did not report the exact pending r2 plan",
        )

        repeat_launch_before = paths["launch"].read_bytes()
        repeat_r1_before = exact_tree(r1_workspace)
        repeat_plan_result = observe_source("repeat-plan-r1-to-r2", source, lambda: plan_refresh(source, home))
        repeated = pending_contract(source, home)
        require(repeat_plan_result["planId"] == plan["id"], "repeat plan returned a different id")
        require(repeated["planPath"].read_bytes() == plan_bytes, "repeat plan changed canonical plan bytes")
        require(digest_bytes(canonical_bytes(repeated["plan"])) == plan_digest, "repeat plan changed the canonical digest")
        require(tree_digest(repeated["candidate"]) == candidate_digest, "repeat plan changed the candidate digest")
        require(exact_tree(repeated["candidate"]) == candidate_tree_before_repeat, "repeat plan changed candidate bytes")
        require(paths["launch"].read_bytes() == repeat_launch_before, "repeat plan changed the launch pointer")
        require(exact_tree(r1_workspace) == repeat_r1_before, "repeat plan changed r1")

        baseline_home_tree = exact_tree(home)
        baseline_source_tree = exact_tree(source)
        probes: list[dict[str, Any]] = []

        def failure_probe(
            identifier: str,
            expected_error: str,
            operation: Callable[[Path], Any],
            *,
            mutate_home: Callable[[dict[str, Any]], None] | None = None,
            mutate_source: Callable[[Path], None] | None = None,
        ) -> None:
            probe_home = runtime_root / f"probe-{identifier}"
            shutil.copytree(home, probe_home)
            contract = pending_contract(source, probe_home)
            if mutate_home is not None:
                mutate_home(contract)
            planned_source_bytes = refresh_target.read_bytes()
            if mutate_source is not None:
                mutate_source(source)
            source_before_operation = exact_tree(source)
            home_before_operation = exact_tree(probe_home)
            launch_before_operation = contract["paths"]["launch"].read_bytes()
            active_before_operation = exact_tree(contract["launchView"]["activeWorkspace"])
            candidate_before_operation = exact_tree(contract["candidate"])
            actual_error = "operation unexpectedly succeeded"
            try:
                observe_source(identifier, source, lambda: operation(probe_home))
            except Exception as error:  # expected error type and message are asserted below
                actual_error = str(error)
            source_unchanged = exact_tree(source) == source_before_operation
            home_unchanged = exact_tree(probe_home) == home_before_operation
            launch_unchanged = contract["paths"]["launch"].read_bytes() == launch_before_operation
            active_unchanged = exact_tree(contract["launchView"]["activeWorkspace"]) == active_before_operation
            candidate_unchanged = exact_tree(contract["candidate"]) == candidate_before_operation
            observed = expected_error in actual_error
            if mutate_source is not None:
                refresh_target.write_bytes(planned_source_bytes)
            require(exact_tree(source) == baseline_source_tree, f"source was not restored after {identifier}")
            require(observed, f"probe {identifier} did not observe expected error: {actual_error}")
            require(source_unchanged, f"probe {identifier} changed source bytes")
            require(home_unchanged, f"probe {identifier} wrote project state after rejection")
            require(launch_unchanged and active_unchanged and candidate_unchanged, f"probe {identifier} changed revision state")
            probes.append(
                {
                    "id": identifier,
                    "expectedError": expected_error,
                    "actualError": actual_error,
                    "expectedFailureObserved": observed,
                    "sourceBytesUnchanged": source_unchanged,
                    "projectBytesUnchangedAfterRejection": home_unchanged,
                    "launchPointerUnchanged": launch_unchanged,
                    "activeWorkspaceUnchanged": active_unchanged,
                    "candidateWorkspaceUnchanged": candidate_unchanged,
                }
            )

        failure_probe(
            "wrong-accept-plan-id",
            "accepted refresh plan id does not match the pending plan",
            lambda probe_home: accept_refresh(source, plan["id"] + ".wrong", probe_home),
        )
        failure_probe(
            "wrong-discard-plan-id",
            "discarded refresh plan id does not match the pending plan",
            lambda probe_home: discard_refresh(source, plan["id"] + ".wrong", probe_home),
        )
        failure_probe(
            "source-drift-after-plan",
            "source changed after refresh planning; discard and plan again",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_source=lambda _source: refresh_target.write_bytes(refresh_target.read_bytes() + b"// drift after plan\n"),
        )
        failure_probe(
            "active-workspace-drift",
            "active project changed after refresh planning; discard and plan again",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: (contract["launchView"]["activeWorkspace"] / "active-drift.txt").write_bytes(b"drift\n"),
        )
        failure_probe(
            "candidate-workspace-drift",
            "refresh candidate changed after planning",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: (contract["candidate"] / "candidate-drift.txt").write_bytes(b"drift\n"),
        )
        failure_probe(
            "status-candidate-workspace-drift",
            "pending refresh candidate digest does not match the plan",
            lambda probe_home: project_status(source, probe_home),
            mutate_home=lambda contract: (contract["candidate"] / "status-candidate-drift.txt").write_bytes(b"drift\n"),
        )
        failure_probe(
            "pending-unexpected-entry",
            "pending refresh directory contains unexpected entries",
            lambda probe_home: discard_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: (contract["planPath"].parent / "foreign.txt").write_bytes(b"must-not-delete\n"),
        )
        failure_probe(
            "plan-role-tamper",
            "pending refresh plan role, schema, scope, or status is invalid",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: mutate_json(contract["planPath"], lambda value: value.__setitem__("artifactRole", "wrong-role")),
        )
        failure_probe(
            "plan-status-tamper",
            "pending refresh plan role, schema, scope, or status is invalid",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: mutate_json(contract["planPath"], lambda value: value.__setitem__("status", "accepted")),
        )
        failure_probe(
            "plan-authority-tamper",
            "pending refresh plan authority is invalid",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: mutate_json(
                contract["planPath"],
                lambda value: value["authority"].__setitem__("targetRepositoryMutation", True),
            ),
        )

        def tamper_transition(contract: dict[str, Any]) -> None:
            def mutation(value: dict[str, Any]) -> None:
                value["toRevision"]["sequence"] = value["fromRevision"]["sequence"] + 2
                value["toRevision"]["id"] = f"revision.r{value['toRevision']['sequence']:04d}"

            mutate_json(contract["planPath"], mutation)

        failure_probe(
            "plan-revision-transition-tamper",
            "pending refresh plan revision transition is invalid",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=tamper_transition,
        )
        failure_probe(
            "weakly-attributed-staged-revision-discard",
            "staged revision cannot be attributed to the pending plan",
            lambda probe_home: discard_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: (
                contract["revisionDestination"].mkdir(parents=True),
                canonical_write(contract["revisionDestination"] / "refresh-receipt.json", {"planId": plan["id"]}),
                (contract["revisionDestination"] / "arbitrary.txt").write_bytes(b"must-not-delete\n"),
            ),
        )

        extra_stage_home = runtime_root / "probe-exact-staged-revision-with-extra-entry-discard"
        shutil.copytree(home, extra_stage_home)
        extra_stage = pending_contract(source, extra_stage_home)
        original_write_json_atomic = igd_refresh.write_json_atomic

        def stop_extra_stage_before_launch(path: Path, value: dict[str, Any]) -> None:
            if Path(path).resolve() == extra_stage["paths"]["launch"].resolve():
                raise InjectedCommitFailure("stage complete before launch commit")
            original_write_json_atomic(path, value)

        igd_refresh.write_json_atomic = stop_extra_stage_before_launch
        try:
            try:
                accept_refresh(source, plan["id"], extra_stage_home)
            except InjectedCommitFailure:
                pass
        finally:
            igd_refresh.write_json_atomic = original_write_json_atomic
        require(extra_stage["revisionDestination"].is_dir(), "exact staged revision was not created for deletion probe")
        extra_file = extra_stage["revisionDestination"] / "foreign.txt"
        extra_file.write_bytes(b"must-not-delete\n")
        extra_stage_launch_before = extra_stage["paths"]["launch"].read_bytes()
        extra_stage_error = "operation unexpectedly succeeded"
        try:
            observe_source(
                "exact-staged-revision-with-extra-entry-discard",
                source,
                lambda: discard_refresh(source, plan["id"], extra_stage_home),
            )
        except Exception as error:
            extra_stage_error = str(error)
        extra_stage_observed = (
            "staged revision contains unexpected entries" in extra_stage_error
            and extra_file.is_file()
            and extra_stage["planPath"].is_file()
            and extra_stage["paths"]["launch"].read_bytes() == extra_stage_launch_before
        )
        require(extra_stage_observed, f"exact staged revision extra-entry probe failed: {extra_stage_error}")
        probes.append(
            {
                "id": "exact-staged-revision-with-extra-entry-discard",
                "expectedError": "staged revision contains unexpected entries",
                "actualError": extra_stage_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "launchPointerUnchanged": True,
                "stagedRevisionPreserved": True,
                "unexpectedEntryPreserved": True,
            }
        )
        failure_probe(
            "revision-destination-collision",
            "staged accepted revision conflicts with the pending candidate",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: (
                contract["revisionDestination"].mkdir(parents=True),
                (contract["revisionDestination"] / "collision.txt").write_bytes(b"collision\n"),
            ),
        )
        failure_probe(
            "launch-pointer-drift",
            "active launch provenance changed after refresh planning",
            lambda probe_home: accept_refresh(source, plan["id"], probe_home),
            mutate_home=lambda contract: mutate_json(
                contract["paths"]["launch"],
                lambda value: value.__setitem__("sourceDigest", "sha256:" + "0" * 64),
            ),
        )

        reparse_home = runtime_root / "probe-refresh-internal-reparse-point"
        shutil.copytree(home, reparse_home)
        reparse_contract = pending_contract(source, reparse_home)
        refresh_path = reparse_contract["paths"]["root"] / REFRESH_DIRECTORY
        shutil.rmtree(refresh_path)
        reparse_target = runtime_root / "refresh-reparse-target"
        reparse_target.mkdir()
        if os.name == "nt":
            created = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(refresh_path), str(reparse_target)],
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            require(created.returncode == 0, f"could not create refresh junction probe: {created.stderr or created.stdout}")
        else:
            refresh_path.symlink_to(reparse_target, target_is_directory=True)
        reparse_launch_before = reparse_contract["paths"]["launch"].read_bytes()
        reparse_active_before = exact_tree(reparse_contract["launchView"]["activeWorkspace"])
        reparse_error = "operation unexpectedly succeeded"
        reparse_status_error = "operation unexpectedly succeeded"
        try:
            observe_source("refresh-internal-reparse-point", source, lambda: plan_refresh(source, reparse_home))
        except Exception as error:
            reparse_error = str(error)
        try:
            observe_source("refresh-internal-reparse-status", source, lambda: project_status(source, reparse_home))
        except Exception as error:
            reparse_status_error = str(error)
        finally:
            refresh_path.rmdir()
        reparse_observed = (
            "local refresh paths must not contain reparse points" in reparse_error
            and "local refresh paths must not contain reparse points" in reparse_status_error
            and reparse_contract["paths"]["launch"].read_bytes() == reparse_launch_before
            and exact_tree(reparse_contract["launchView"]["activeWorkspace"]) == reparse_active_before
            and not any(reparse_target.iterdir())
        )
        require(reparse_observed, f"refresh internal reparse probe failed: {reparse_error}")
        probes.append(
            {
                "id": "refresh-internal-reparse-point",
                "expectedError": "local refresh paths must not contain reparse points",
                "actualError": reparse_error,
                "statusActualError": reparse_status_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "launchPointerUnchanged": True,
                "activeWorkspaceUnchanged": True,
                "reparseTargetUnchanged": True,
            }
        )

        plan_link_home = runtime_root / "probe-refresh-plan-file-reparse-point"
        shutil.copytree(home, plan_link_home)
        plan_link_contract = pending_contract(source, plan_link_home)
        external_plan = runtime_root / "external-refresh-plan.json"
        external_plan.write_bytes(plan_link_contract["planPath"].read_bytes())
        plan_link_contract["planPath"].unlink()
        try:
            plan_link_contract["planPath"].symlink_to(external_plan)
        except OSError as error:
            raise HarnessError(f"could not create refresh plan file symlink probe: {error}") from error
        plan_link_launch_before = plan_link_contract["paths"]["launch"].read_bytes()
        plan_link_active_before = exact_tree(plan_link_contract["launchView"]["activeWorkspace"])
        external_plan_before = external_plan.read_bytes()
        plan_link_error = "operation unexpectedly succeeded"
        plan_link_accept_error = "operation unexpectedly succeeded"
        plan_link_discard_error = "operation unexpectedly succeeded"
        try:
            observe_source(
                "refresh-plan-file-reparse-point",
                source,
                lambda: project_status(source, plan_link_home),
            )
        except Exception as error:
            plan_link_error = str(error)
        try:
            observe_source(
                "refresh-plan-file-reparse-accept",
                source,
                lambda: accept_refresh(source, plan["id"], plan_link_home),
            )
        except Exception as error:
            plan_link_accept_error = str(error)
        try:
            observe_source(
                "refresh-plan-file-reparse-discard",
                source,
                lambda: discard_refresh(source, plan["id"], plan_link_home),
            )
        except Exception as error:
            plan_link_discard_error = str(error)
        plan_link_observed = (
            "local refresh plan path must not contain reparse points" in plan_link_error
            and "local refresh plan path must not contain reparse points" in plan_link_accept_error
            and "local refresh plan path must not contain reparse points" in plan_link_discard_error
            and plan_link_contract["paths"]["launch"].read_bytes() == plan_link_launch_before
            and exact_tree(plan_link_contract["launchView"]["activeWorkspace"]) == plan_link_active_before
            and external_plan.read_bytes() == external_plan_before
        )
        require(plan_link_observed, f"refresh plan file reparse probe failed: {plan_link_error}")
        probes.append(
            {
                "id": "refresh-plan-file-reparse-point",
                "expectedError": "local refresh plan path must not contain reparse points",
                "actualError": plan_link_error,
                "acceptActualError": plan_link_accept_error,
                "discardActualError": plan_link_discard_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "launchPointerUnchanged": True,
                "activeWorkspaceUnchanged": True,
                "reparseTargetUnchanged": True,
            }
        )

        failure_probe(
            "no-change-cleanup-pending-extra-entry",
            "pending refresh directory contains unexpected entries",
            lambda probe_home: plan_refresh(source, probe_home),
            mutate_home=lambda contract: (contract["planPath"].parent / "foreign.txt").write_bytes(b"must-not-delete\n"),
            mutate_source=lambda _source: refresh_target.write_bytes(first_source_before),
        )

        changed_source_bytes = refresh_target.read_bytes()
        refresh_target.write_bytes(first_source_before)
        no_change_link_error = "operation unexpectedly succeeded"
        try:
            try:
                observe_source(
                    "no-change-cleanup-plan-file-reparse",
                    source,
                    lambda: plan_refresh(source, plan_link_home),
                )
            except Exception as error:
                no_change_link_error = str(error)
        finally:
            refresh_target.write_bytes(changed_source_bytes)
        no_change_link_observed = (
            "local refresh plan path must not contain reparse points" in no_change_link_error
            and plan_link_contract["planPath"].is_symlink()
            and external_plan.read_bytes() == external_plan_before
            and exact_tree(source) == baseline_source_tree
        )
        require(no_change_link_observed, f"no-change plan symlink cleanup probe failed: {no_change_link_error}")
        probes.append(
            {
                "id": "no-change-cleanup-plan-file-reparse",
                "expectedError": "local refresh plan path must not contain reparse points",
                "actualError": no_change_link_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "pendingPlanPreserved": True,
                "reparseTargetUnchanged": True,
            }
        )

        immutable_home = runtime_root / "probe-target-source-immutability"
        shutil.copytree(home, immutable_home)
        immutable_home_before = exact_tree(immutable_home)
        immutable_source_before = exact_tree(source)
        immutable_result = observe_source(
            "target-source-immutability",
            source,
            lambda: plan_refresh(source, immutable_home),
        )
        immutable_observed = (
            immutable_result["result"] == "review-required"
            and exact_tree(source) == immutable_source_before
            and exact_tree(immutable_home) == immutable_home_before
        )
        require(immutable_observed, "repeat planning did not preserve target source and pending project bytes")
        probes.append(
            {
                "id": "target-source-immutability",
                "expectedCondition": "repeat planning performs no target-source or pending-state write",
                "expectedFailureObserved": immutable_observed,
                "sourceBytesUnchanged": True,
                "projectBytesUnchangedAfterRejection": True,
                "operationResult": immutable_result["result"],
            }
        )

        precommit_home = runtime_root / "probe-injected-failure-before-launch-commit"
        shutil.copytree(home, precommit_home)
        precommit = pending_contract(source, precommit_home)
        precommit_launch_bytes = precommit["paths"]["launch"].read_bytes()
        precommit_active_tree = exact_tree(precommit["launchView"]["activeWorkspace"])
        original_write_json_atomic = igd_refresh.write_json_atomic

        def fail_before_launch_write(path: Path, value: dict[str, Any]) -> None:
            if Path(path).resolve() == precommit["paths"]["launch"].resolve():
                raise InjectedCommitFailure("injected failure before atomic launch pointer commit")
            original_write_json_atomic(path, value)

        precommit_error = "operation unexpectedly succeeded"
        igd_refresh.write_json_atomic = fail_before_launch_write
        try:
            try:
                observe_source(
                    "injected-failure-before-launch-commit",
                    source,
                    lambda: accept_refresh(source, plan["id"], precommit_home),
                )
            except InjectedCommitFailure as error:
                precommit_error = str(error)
        finally:
            igd_refresh.write_json_atomic = original_write_json_atomic
        precommit_view = validate_launch_record(read_json(precommit["paths"]["launch"]), source, precommit["paths"]["root"])
        staged_precommit_workspace = precommit["revisionDestination"] / "workspace"
        validate_project_workspace(staged_precommit_workspace)
        precommit_observed = (
            "before atomic launch pointer commit" in precommit_error
            and precommit["paths"]["launch"].read_bytes() == precommit_launch_bytes
            and precommit_view["activeRevision"]["id"] == "revision.r0001"
            and exact_tree(precommit_view["activeWorkspace"]) == precommit_active_tree
            and staged_precommit_workspace.is_dir()
            and precommit["planPath"].is_file()
        )
        precommit_cleanup = observe_source(
            "pre-commit-discard-removes-exact-staged-revision",
            source,
            lambda: discard_refresh(source, plan["id"], precommit_home),
        )
        precommit_after_cleanup = validate_launch_record(
            read_json(precommit["paths"]["launch"]), source, precommit["paths"]["root"]
        )
        precommit_observed = (
            precommit_observed
            and precommit_cleanup["action"] == "discarded"
            and precommit_after_cleanup["activeRevision"]["id"] == "revision.r0001"
            and not precommit["revisionDestination"].exists()
            and not precommit["planPath"].exists()
        )
        require(precommit_observed, "pre-commit injection did not leave r1 active with a recoverable staged r2")
        probes.append(
            {
                "id": "injected-failure-before-launch-commit",
                "expectedError": "injected failure before atomic launch pointer commit",
                "actualError": precommit_error,
                "expectedFailureObserved": precommit_observed,
                "sourceBytesUnchanged": True,
                "activeRevisionAfterInterruption": precommit_view["activeRevision"]["id"],
                "stagedCandidateRecoverable": True,
                "pendingPlanRecoverable": True,
                "exactDiscardRemovedOnlyStagedRevision": True,
                "pendingCleanupAction": precommit_cleanup["action"],
            }
        )

        late_mutation_home = runtime_root / "probe-late-workspace-mutation-before-launch-commit"
        shutil.copytree(home, late_mutation_home)
        late_mutation = pending_contract(source, late_mutation_home)
        late_launch_before = late_mutation["paths"]["launch"].read_bytes()
        original_write_json_atomic = igd_refresh.write_json_atomic

        def mutate_revision_before_launch_write(path: Path, value: dict[str, Any]) -> None:
            if Path(path).resolve() == late_mutation["paths"]["launch"].resolve():
                (late_mutation["revisionDestination"] / "workspace" / "late-tamper.txt").write_bytes(b"late tamper\n")
            original_write_json_atomic(path, value)

        late_mutation_error = "operation unexpectedly succeeded"
        igd_refresh.write_json_atomic = mutate_revision_before_launch_write
        try:
            try:
                observe_source(
                    "late-workspace-mutation-before-launch-commit",
                    source,
                    lambda: accept_refresh(source, plan["id"], late_mutation_home),
                )
            except Exception as error:
                late_mutation_error = str(error)
        finally:
            igd_refresh.write_json_atomic = original_write_json_atomic
        late_view = validate_launch_record(
            read_json(late_mutation["paths"]["launch"]), source, late_mutation["paths"]["root"]
        )
        late_mutation_observed = (
            "accepted revision failed post-commit validation; prior launch restored" in late_mutation_error
            and late_mutation["paths"]["launch"].read_bytes() == late_launch_before
            and late_view["activeRevision"]["id"] == "revision.r0001"
            and late_mutation["revisionDestination"].is_dir()
            and late_mutation["planPath"].is_file()
        )
        require(late_mutation_observed, f"late workspace mutation probe failed: {late_mutation_error}")
        probes.append(
            {
                "id": "late-workspace-mutation-before-launch-commit",
                "expectedError": "accepted revision failed post-commit validation; prior launch restored",
                "actualError": late_mutation_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "activeRevisionAfterRecovery": late_view["activeRevision"]["id"],
                "launchPointerRestored": True,
                "invalidRevisionNotActivated": True,
            }
        )

        postcommit_home = runtime_root / "probe-injected-failure-after-launch-commit"
        shutil.copytree(home, postcommit_home)
        postcommit = pending_contract(source, postcommit_home)
        original_rmtree = igd_refresh.shutil.rmtree

        def fail_after_launch_write(path: Path, *args: Any, **kwargs: Any) -> None:
            if Path(path).resolve() == postcommit["planPath"].parent.resolve():
                raise InjectedCommitFailure("injected failure after atomic launch pointer commit")
            original_rmtree(path, *args, **kwargs)

        postcommit_error = "operation unexpectedly succeeded"
        igd_refresh.shutil.rmtree = fail_after_launch_write
        try:
            try:
                observe_source(
                    "injected-failure-after-launch-commit",
                    source,
                    lambda: accept_refresh(source, plan["id"], postcommit_home),
                )
            except InjectedCommitFailure as error:
                postcommit_error = str(error)
        finally:
            igd_refresh.shutil.rmtree = original_rmtree
        postcommit_view = validate_launch_record(read_json(postcommit["paths"]["launch"]), source, postcommit["paths"]["root"])
        validate_project_workspace(postcommit_view["activeWorkspace"])
        validate_project_workspace(relative_workspace(postcommit["paths"]["root"], postcommit_view["archivedRevisions"][0]["workspace"]))
        postcommit_observed = (
            "after atomic launch pointer commit" in postcommit_error
            and postcommit_view["activeRevision"]["id"] == "revision.r0002"
            and [record["id"] for record in postcommit_view["archivedRevisions"]] == ["revision.r0001"]
            and postcommit["planPath"].is_file()
        )
        postcommit_cleanup = observe_source(
            "post-commit-discard-cleans-pending-only",
            source,
            lambda: discard_refresh(source, plan["id"], postcommit_home),
        )
        postcommit_after_cleanup = validate_launch_record(
            read_json(postcommit["paths"]["launch"]), source, postcommit["paths"]["root"]
        )
        postcommit_observed = (
            postcommit_observed
            and postcommit_cleanup["action"] == "accepted-plan-cleanup"
            and postcommit_after_cleanup["activeRevision"]["id"] == "revision.r0002"
            and postcommit["revisionDestination"].is_dir()
            and not postcommit["planPath"].exists()
        )
        require(postcommit_observed, "post-commit injection did not leave r2 active and independently valid")
        probes.append(
            {
                "id": "injected-failure-after-launch-commit",
                "expectedError": "injected failure after atomic launch pointer commit",
                "actualError": postcommit_error,
                "expectedFailureObserved": postcommit_observed,
                "sourceBytesUnchanged": True,
                "activeRevisionAfterInterruption": postcommit_view["activeRevision"]["id"],
                "historicalWorkspaceValid": True,
                "activeWorkspaceValid": True,
                "discardAfterCommitPreservedActiveRevision": True,
                "pendingCleanupAction": postcommit_cleanup["action"],
            }
        )

        pre_accept_probe_ids = PROBE_IDS[: PROBE_IDS.index("historical-revision-digest-tamper")]
        require([probe["id"] for probe in probes] == pre_accept_probe_ids, "pre-accept negative probe list or order changed")
        require(all(probe["expectedFailureObserved"] for probe in probes), "one or more pre-accept negative probes failed")
        require(exact_tree(home) == baseline_home_tree, "negative probe copies changed the positive pending home")
        require(exact_tree(source) == baseline_source_tree, "negative probes changed the positive source baseline")

        launch_before_accept = paths["launch"].read_bytes()
        r1_before_accept = exact_tree(r1_workspace)
        source_before_accept = exact_tree(source)
        accepted_r2 = observe_source("accept-r1-to-r2", source, lambda: accept_refresh(source, plan["id"], home))
        require(accepted_r2["result"] == "pass" and accepted_r2["activeRevisionChanged"] is True, "exact r2 acceptance failed")
        require(paths["launch"].read_bytes() != launch_before_accept, "acceptance did not atomically change the launch pointer")
        require(exact_tree(r1_workspace) == r1_before_accept, "r1 changed during r2 acceptance")
        require(exact_tree(source) == source_before_accept, "r2 acceptance changed source bytes")

        launch_r2 = read_json(paths["launch"])
        view_r2 = validate_launch_record(launch_r2, source, paths["root"])
        require(view_r2["activeRevision"]["id"] == "revision.r0002", "r2 is not active after acceptance")
        require([record["id"] for record in view_r2["archivedRevisions"]] == ["revision.r0001"], "r1 is not the sole archived revision")
        archived_r1 = relative_workspace(paths["root"], view_r2["archivedRevisions"][0]["workspace"])
        active_r2 = view_r2["activeWorkspace"]
        archived_r1_state, _, _, archived_r1_data = validate_project_workspace(archived_r1)
        active_r2_state, _, _, active_r2_data = validate_project_workspace(active_r2)
        require(exact_tree(archived_r1) == sealed_r1_tree and tree_digest(archived_r1) == sealed_r1_digest, "archived r1 is not byte-identical to sealed r1")
        require(exact_tree(active_r2) == candidate_tree_before_repeat and tree_digest(active_r2) == candidate_digest, "active r2 does not match the reviewed candidate")
        require(retained_mapping_id in {item["id"] for item in active_r2_state["mappings"]}, "retained mapping is absent from r2")
        require(stale_mapping_id not in {item["id"] for item in active_r2_state["mappings"]}, "stale mapping remained active in r2")
        require(stale_mapping_id in {item["id"] for item in archived_r1_state["mappings"]}, "stale mapping is not recoverable from r1")
        require(PROPOSAL_ID in {item["id"] for item in archived_r1_data["proposals"]}, "proposal is not recoverable from r1")
        require(PROPOSAL_ID not in {item["id"] for item in active_r2_data["proposals"]}, "proposal remained active in r2")
        stale_work_r2 = next(item for item in active_r2_state["workItems"] if item["id"] == STALE_WORK_ID)
        retained_work_r2 = next(item for item in active_r2_state["workItems"] if item["id"] == RETAINED_WORK_ID)
        require(
            stale_work_r2["status"] == "intake"
            and stale_work_r2["mappingStatus"] == "unmapped"
            and retained_work_r2["status"] == "mapping-candidate"
            and retained_work_r2["mappingStatus"] == "candidate",
            "r2 work-item lifecycle normalization is invalid",
        )
        receipt_r2 = read_json(active_r2.parent / "refresh-receipt.json")
        accepted_plan_r2 = read_json(active_r2.parent / ACCEPTED_REFRESH_PLAN_FILE)
        require(
            receipt_r2["artifactRole"] == REFRESH_RECEIPT_ROLE
            and receipt_r2["planId"] == plan["id"]
            and receipt_r2["planDigest"] == plan_digest,
            "r2 receipt does not bind the accepted plan",
        )
        require(
            accepted_plan_r2 == plan and digest_bytes(canonical_bytes(accepted_plan_r2)) == plan_digest,
            "r2 did not preserve the canonical accepted plan",
        )
        require(not (paths["root"] / REFRESH_DIRECTORY / "pending").exists(), "r2 pending plan was not removed")

        status_after_r2 = observe_source("status-active-r2", source, lambda: project_status(source, home))
        require(status_after_r2["result"] == "pass" and status_after_r2["sourceDigest"] == plan["toRevision"]["sourceDigest"], "normal status did not resume at r2")

        historical_tamper_home = runtime_root / "probe-historical-revision-digest-tamper"
        shutil.copytree(home, historical_tamper_home)
        historical_paths = project_paths(source, historical_tamper_home)
        historical_launch = read_json(historical_paths["launch"])
        historical_view = validate_launch_record(historical_launch, source, historical_paths["root"])
        historical_workspace = relative_workspace(
            historical_paths["root"], historical_view["archivedRevisions"][0]["workspace"]
        )
        (historical_workspace / "tamper.txt").write_bytes(b"tamper\n")
        historical_launch_before = historical_paths["launch"].read_bytes()
        historical_error = "operation unexpectedly succeeded"
        try:
            observe_source(
                "historical-revision-digest-tamper",
                source,
                lambda: project_status(source, historical_tamper_home),
            )
        except Exception as error:
            historical_error = str(error)
        historical_observed = (
            "local revision workspace digest does not match launch provenance" in historical_error
            and historical_paths["launch"].read_bytes() == historical_launch_before
        )
        require(historical_observed, f"historical revision digest tamper probe failed: {historical_error}")
        probes.append(
            {
                "id": "historical-revision-digest-tamper",
                "expectedError": "local revision workspace digest does not match launch provenance",
                "actualError": historical_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "launchPointerUnchanged": True,
                "historicalTamperDetected": True,
            }
        )

        historical_source_home = runtime_root / "probe-historical-revision-source-provenance-tamper"
        shutil.copytree(home, historical_source_home)
        historical_source_paths = project_paths(source, historical_source_home)
        mutate_json(
            historical_source_paths["launch"],
            lambda value: value["archivedRevisions"][0].__setitem__("sourceDigest", "sha256:" + "0" * 64),
        )
        historical_source_error = "operation unexpectedly succeeded"
        try:
            observe_source(
                "historical-revision-source-provenance-tamper",
                source,
                lambda: project_status(source, historical_source_home),
            )
        except Exception as error:
            historical_source_error = str(error)
        require(
            "local revision source digest does not match workspace provenance" in historical_source_error,
            f"historical source provenance tamper probe failed: {historical_source_error}",
        )
        probes.append(
            {
                "id": "historical-revision-source-provenance-tamper",
                "expectedError": "local revision source digest does not match workspace provenance",
                "actualError": historical_source_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "sourceProvenanceTamperDetected": True,
            }
        )

        receipt_tamper_home = runtime_root / "probe-active-revision-receipt-provenance-tamper"
        shutil.copytree(home, receipt_tamper_home)
        receipt_tamper_paths = project_paths(source, receipt_tamper_home)
        mutate_json(
            receipt_tamper_paths["launch"],
            lambda value: value["activeRevision"].__setitem__("activatedByPlanDigest", "sha256:" + "0" * 64),
        )
        receipt_tamper_error = "operation unexpectedly succeeded"
        try:
            observe_source(
                "active-revision-receipt-provenance-tamper",
                source,
                lambda: project_status(source, receipt_tamper_home),
            )
        except Exception as error:
            receipt_tamper_error = str(error)
        require(
            "local revision accepted plan does not match launch provenance" in receipt_tamper_error,
            f"active receipt provenance tamper probe failed: {receipt_tamper_error}",
        )
        probes.append(
            {
                "id": "active-revision-receipt-provenance-tamper",
                "expectedError": "local revision accepted plan does not match launch provenance",
                "actualError": receipt_tamper_error,
                "expectedFailureObserved": True,
                "sourceBytesUnchanged": True,
                "receiptProvenanceTamperDetected": True,
            }
        )

        def accepted_status_tamper_probe(
            identifier: str,
            expected_error: str,
            mutation: Callable[[dict[str, Path], dict[str, Any]], None],
        ) -> None:
            probe_home = runtime_root / f"probe-{identifier}"
            shutil.copytree(home, probe_home)
            probe_paths = project_paths(source, probe_home)
            probe_launch = read_json(probe_paths["launch"])
            probe_view = validate_launch_record(probe_launch, source, probe_paths["root"])
            mutation(probe_paths, probe_view)
            source_before = exact_tree(source)
            home_before = exact_tree(probe_home)
            actual_error = "operation unexpectedly succeeded"
            try:
                observe_source(identifier, source, lambda: project_status(source, probe_home))
            except Exception as error:
                actual_error = str(error)
            observed = expected_error in actual_error
            require(observed, f"probe {identifier} did not observe expected error: {actual_error}")
            require(exact_tree(source) == source_before, f"probe {identifier} changed source bytes")
            require(exact_tree(probe_home) == home_before, f"probe {identifier} changed project bytes")
            probes.append(
                {
                    "id": identifier,
                    "expectedError": expected_error,
                    "actualError": actual_error,
                    "expectedFailureObserved": True,
                    "sourceBytesUnchanged": True,
                    "projectBytesUnchangedAfterRejection": True,
                }
            )

        def mutate_receipt_authority(_paths: dict[str, Path], view: dict[str, Any]) -> None:
            mutate_json(
                view["activeWorkspace"].parent / "refresh-receipt.json",
                lambda value: value["authority"].__setitem__("targetRepositoryMutation", True),
            )

        accepted_status_tamper_probe(
            "receipt-authority-tamper",
            "local revision activation receipt does not match launch provenance",
            mutate_receipt_authority,
        )

        def mutate_receipt_structure(_paths: dict[str, Path], view: dict[str, Any]) -> None:
            def mutation(value: dict[str, Any]) -> None:
                value["fromRevision"]["id"] = "revision.r9999"
                value["priorWorkspace"] = "revisions/revision.r9999/workspace"
                value["sourcePathPersisted"] = True

            mutate_json(view["activeWorkspace"].parent / "refresh-receipt.json", mutation)

        accepted_status_tamper_probe(
            "receipt-structural-provenance-tamper",
            "local revision activation receipt does not match launch provenance",
            mutate_receipt_structure,
        )

        def mutate_joint_plan_digest(probe_paths: dict[str, Path], view: dict[str, Any]) -> None:
            forged_digest = "sha256:" + "0" * 64
            mutate_json(
                probe_paths["launch"],
                lambda value: value["activeRevision"].__setitem__("activatedByPlanDigest", forged_digest),
            )
            mutate_json(
                view["activeWorkspace"].parent / "refresh-receipt.json",
                lambda value: value.__setitem__("planDigest", forged_digest),
            )

        accepted_status_tamper_probe(
            "receipt-joint-plan-digest-tamper",
            "local revision activation receipt does not match launch provenance",
            mutate_joint_plan_digest,
        )

        def mutate_accepted_plan(_paths: dict[str, Path], view: dict[str, Any]) -> None:
            mutate_json(
                view["activeWorkspace"].parent / ACCEPTED_REFRESH_PLAN_FILE,
                lambda value: value["sourceDelta"]["changedPaths"].append("forged.cs"),
            )

        accepted_status_tamper_probe(
            "accepted-plan-artifact-tamper",
            "local revision activation receipt does not match launch provenance",
            mutate_accepted_plan,
        )

        def mutate_all_plan_provenance(probe_paths: dict[str, Path], view: dict[str, Any]) -> None:
            accepted_plan_path = view["activeWorkspace"].parent / ACCEPTED_REFRESH_PLAN_FILE
            accepted_plan = read_json(accepted_plan_path)
            accepted_plan["sourceDelta"]["changedPaths"].append("coordinated-forgery.cs")
            canonical_write(accepted_plan_path, accepted_plan)
            forged_digest = digest_bytes(canonical_bytes(accepted_plan))
            mutate_json(
                view["activeWorkspace"].parent / "refresh-receipt.json",
                lambda value: value.__setitem__("planDigest", forged_digest),
            )
            mutate_json(
                probe_paths["launch"],
                lambda value: value["activeRevision"].__setitem__("activatedByPlanDigest", forged_digest),
            )

        accepted_status_tamper_probe(
            "coordinated-accepted-plan-provenance-tamper",
            "local revision accepted plan semantics do not match preserved workspaces",
            mutate_all_plan_provenance,
        )
        require([probe["id"] for probe in probes] == PROBE_IDS, "negative probe list or order changed")
        require(all(probe["expectedFailureObserved"] for probe in probes), "one or more negative probes failed")

        second_source = source / "SecondRefresh.cs"
        second_source.write_bytes(
            b"namespace ProductSmoke;\n\n"
            b"public static class SecondRefresh\n"
            b"{\n"
            b"    public static int Value() => 3;\n"
            b"}\n"
        )
        second_changed_source = exact_tree(source)
        second_changed_source_digest = tree_digest(source)
        r1_before_second_plan = exact_tree(archived_r1)
        r2_before_second_plan = exact_tree(active_r2)
        launch_before_second_plan = paths["launch"].read_bytes()
        second_plan_result = observe_source("plan-r2-to-r3", source, lambda: plan_refresh(source, home))
        require(second_plan_result["result"] == "review-required", "second refresh was not planned")
        second_pending = pending_contract(source, home)
        second_plan = second_pending["plan"]
        second_plan_digest = digest_bytes(canonical_bytes(second_plan))
        second_candidate_tree = exact_tree(second_pending["candidate"])
        second_candidate_digest = tree_digest(second_pending["candidate"])
        validate_project_workspace(second_pending["candidate"])
        require(second_plan["fromRevision"]["id"] == "revision.r0002" and second_plan["toRevision"]["id"] == "revision.r0003", "second plan is not r2 to r3")
        require(second_plan["sourceDelta"]["addedPaths"] == ["SecondRefresh.cs"], "second plan did not record the added source file")
        require(second_plan["invalidation"]["retainedMappingIds"] == [retained_mapping_id], "retained mapping did not survive the r3 plan")
        require(not second_plan["invalidation"]["staleMappingIds"] and not second_plan["invalidation"]["staleProposalIds"], "r3 plan reported unexpected stale lifecycle records")
        require(paths["launch"].read_bytes() == launch_before_second_plan, "r3 planning changed the launch pointer")
        require(exact_tree(archived_r1) == r1_before_second_plan and exact_tree(active_r2) == r2_before_second_plan, "r3 planning changed an existing revision")
        require(exact_tree(source) == second_changed_source, "r3 planning changed source bytes")

        source_before_second_accept = exact_tree(source)
        accepted_r3 = observe_source("accept-r2-to-r3", source, lambda: accept_refresh(source, second_plan["id"], home))
        require(accepted_r3["result"] == "pass" and accepted_r3["toRevision"]["id"] == "revision.r0003", "exact r3 acceptance failed")
        require(exact_tree(source) == source_before_second_accept, "r3 acceptance changed source bytes")

        launch_r3 = read_json(paths["launch"])
        view_r3 = validate_launch_record(launch_r3, source, paths["root"])
        revision_ids = [record["id"] for record in view_r3["archivedRevisions"]] + [view_r3["activeRevision"]["id"]]
        require(revision_ids == ["revision.r0001", "revision.r0002", "revision.r0003"], "revision chain is not contiguous through r3")
        revision_paths = {
            record["id"]: relative_workspace(paths["root"], record["workspace"])
            for record in [*view_r3["archivedRevisions"], view_r3["activeRevision"]]
        }
        revision_states: dict[str, dict[str, Any]] = {}
        revision_data: dict[str, dict[str, Any]] = {}
        for revision_id, workspace in revision_paths.items():
            state, _, _, data = validate_project_workspace(workspace)
            revision_states[revision_id] = state
            revision_data[revision_id] = data
        require(exact_tree(revision_paths["revision.r0001"]) == sealed_r1_tree, "r1 changed after the second acceptance")
        require(exact_tree(revision_paths["revision.r0002"]) == r2_before_second_plan, "r2 changed after the second acceptance")
        require(exact_tree(revision_paths["revision.r0003"]) == second_candidate_tree, "r3 does not match its reviewed candidate")
        require(tree_digest(revision_paths["revision.r0003"]) == second_candidate_digest, "r3 digest does not match its candidate")
        require(
            [item["id"] for item in revision_states["revision.r0003"]["mappings"]] == [retained_mapping_id],
            "r3 active mapping set is invalid",
        )
        require(
            PROPOSAL_ID in {item["id"] for item in revision_data["revision.r0001"]["proposals"]}
            and all(PROPOSAL_ID not in {item["id"] for item in revision_data[revision_id]["proposals"]} for revision_id in ("revision.r0002", "revision.r0003")),
            "proposal lifecycle is not historical-only",
        )
        receipt_r3 = read_json(revision_paths["revision.r0003"].parent / "refresh-receipt.json")
        require(receipt_r3["planId"] == second_plan["id"] and receipt_r3["planDigest"] == second_plan_digest, "r3 receipt does not bind the second plan")

        status_after_r3 = observe_source("status-active-r3", source, lambda: project_status(source, home))
        require(status_after_r3["result"] == "pass" and status_after_r3["sourceDigest"] == second_plan["toRevision"]["sourceDigest"], "normal status did not resume at r3")
        not_required = observe_source("refresh-not-required-r3", source, lambda: plan_refresh(source, home))
        require(not_required["result"] == "pass" and not_required["action"] == "not-required", "unchanged r3 source did not report not-required")
        require(not (paths["root"] / REFRESH_DIRECTORY / "pending").exists(), "a no-change refresh created a pending plan")

        require(exact_tree(FIXTURE) == fixture_before, "repository fixture bytes changed")
        require(all(item["sourceBytesUnchanged"] for item in source_checks), "one or more IGD operations changed source bytes")

        report = {
            "artifactRole": REPORT_ROLE,
            "schemaVersion": "0.1.0",
            "scope": REFRESH_PLAN_SCOPE,
            "status": REPORT_STATUS,
            "result": "pass",
            "probeCount": len(probes),
            "probeIds": PROBE_IDS,
            "probes": probes,
            "positiveEvidence": {
                "fixture": {
                    "sourceFileCountAtPrepare": prepared["sourceFileCount"],
                    "initialSourceTreeDigest": initial_source_digest,
                    "firstChangedSourceTreeDigest": first_changed_source_digest,
                    "secondChangedSourceTreeDigest": second_changed_source_digest,
                    "repositoryFixtureUnchanged": True,
                },
                "overlayLifecycle": {
                    "retainedCodeFactId": retained_fact["id"],
                    "staleCodeFactId": stale_fact["id"],
                    "retainedMappingId": retained_mapping_id,
                    "staleMappingId": stale_mapping_id,
                    "proposalId": PROPOSAL_ID,
                    "proposalApplicationStatus": r1_proposal["applicationStatus"],
                    "proposalHistoricalOnly": True,
                    "r2WorkItemNormalizationValid": True,
                },
                "firstPlan": {
                    "planId": plan["id"],
                    "planDigest": plan_digest,
                    "fromRevision": plan["fromRevision"]["id"],
                    "toRevision": plan["toRevision"]["id"],
                    "sourceDeltaCounts": delta_counts(plan["sourceDelta"]),
                    "codeFactDeltaCounts": delta_counts(plan["codeFactDelta"]),
                    "relationDeltaCounts": delta_counts(plan["relationDelta"]),
                    "retainedMappingCount": len(plan["invalidation"]["retainedMappingIds"]),
                    "staleMappingCount": len(plan["invalidation"]["staleMappingIds"]),
                    "staleProposalCount": len(plan["invalidation"]["staleProposalIds"]),
                    "activeWorkspaceTreeDigest": sealed_r1_digest,
                    "candidateWorkspaceTreeDigest": candidate_digest,
                    "activeWorkspaceBytesUnchanged": True,
                    "launchBytesUnchanged": True,
                    "sourceBytesUnchanged": True,
                    "statusReviewRequired": True,
                    "repeatPlanIdEqual": True,
                    "repeatPlanBytesEqual": True,
                    "repeatPlanDigestEqual": True,
                    "repeatCandidateDigestEqual": True,
                },
                "acceptance": {
                    "firstAcceptedRevision": accepted_r2["toRevision"]["id"],
                    "secondAcceptedRevision": accepted_r3["toRevision"]["id"],
                    "revisionSequence": revision_ids,
                    "revisionTreeDigests": {
                        revision_id: tree_digest(workspace)
                        for revision_id, workspace in sorted(revision_paths.items())
                    },
                    "workspaceValidation": {revision_id: "pass" for revision_id in revision_ids},
                    "r1SealedAndRecoverable": True,
                    "r2HistoricalAndRecoverable": True,
                    "r3ActiveAndValid": True,
                    "launchUsesR3Digest": launch_r3["sourceDigest"] == second_plan["toRevision"]["sourceDigest"],
                    "statusUsesR3Digest": status_after_r3["sourceDigest"] == second_plan["toRevision"]["sourceDigest"],
                    "subsequentRefreshNotRequired": True,
                },
                "secondPlan": {
                    "planId": second_plan["id"],
                    "planDigest": second_plan_digest,
                    "fromRevision": second_plan["fromRevision"]["id"],
                    "toRevision": second_plan["toRevision"]["id"],
                    "sourceDeltaCounts": delta_counts(second_plan["sourceDelta"]),
                    "codeFactDeltaCounts": delta_counts(second_plan["codeFactDelta"]),
                    "relationDeltaCounts": delta_counts(second_plan["relationDelta"]),
                    "candidateWorkspaceTreeDigest": second_candidate_digest,
                    "retainedMappingCount": len(second_plan["invalidation"]["retainedMappingIds"]),
                },
                "interruptionResults": {
                    "preCommit": "prior-r1-active",
                    "postCommit": "new-r2-active",
                    "monkeypatching": "tested-in-process",
                },
                "sourceImmutability": {
                    "operationCount": len(source_checks),
                    "allIgdOperationsByteStable": True,
                    "operations": source_checks,
                },
            },
            "authorityFlags": {
                "planAuthority": REFRESH_AUTHORITY,
                "acceptAuthority": REFRESH_ACCEPT_AUTHORITY,
                "targetRepositoryMutationByIgd": False,
                "externalTemporarySourceMutationPerformedByHarness": True,
            },
            "nonAuthorityFlags": {
                "aiJudgmentUsed": False,
                "automaticCodeApplication": False,
                "automaticIntentMapping": False,
                "approvalAutomation": False,
                "credentialAccessAllowed": False,
                "networkRequired": False,
                "providerApiAllowed": False,
                "targetBuildExecuted": False,
                "targetLaunchExecuted": False,
                "targetRestoreExecuted": False,
            },
        }
        return report
    finally:
        if runtime_root.exists():
            shutil.rmtree(runtime_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="Canonical JSON report path outside the source fixture.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.out.resolve()
    runtime_root = Path(tempfile.gettempdir()).resolve() / RUNTIME_DIRECTORY
    if output == Path(__file__).resolve() or output.is_relative_to(FIXTURE.resolve()) or output.is_relative_to(runtime_root):
        raise SystemExit("error: output must not overwrite harness inputs or temporary source state")
    report = run()
    canonical_write(output, report)
    print(json.dumps({"out": output.as_posix(), "probeCount": report["probeCount"], "result": report["result"]}, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
