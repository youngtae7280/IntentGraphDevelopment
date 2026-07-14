"""Pure deterministic semantics shared by refresh planning and revision validation."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from experimental_csharp_project import (
    empty_semantic_foundation,
    empty_semantic_relation_overlay,
    state_for,
    validate_project_workspace,
)
from experimental_csharp_workspace import csharp_source_records


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def record_map(values: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list):
        return {}
    return {
        item["id"]: item
        for item in values
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def record_delta(before: Any, after: Any) -> dict[str, list[str]]:
    before_by_id = record_map(before)
    after_by_id = record_map(after)
    before_ids = set(before_by_id)
    after_ids = set(after_by_id)
    return {
        "addedIds": sorted(after_ids - before_ids),
        "removedIds": sorted(before_ids - after_ids),
        "changedIds": sorted(
            identifier
            for identifier in before_ids & after_ids
            if canonical_bytes(before_by_id[identifier]) != canonical_bytes(after_by_id[identifier])
        ),
    }


def file_delta(before_records: list[dict[str, str]], after_records: list[dict[str, str]]) -> dict[str, list[str]]:
    before = {record["path"]: record["sha256"] for record in before_records}
    after = {record["path"]: record["sha256"] for record in after_records}
    return {
        "addedPaths": sorted(set(after) - set(before)),
        "removedPaths": sorted(set(before) - set(after)),
        "changedPaths": sorted(path for path in set(before) & set(after) if before[path] != after[path]),
    }


def candidate_state(
    old_state: dict[str, Any],
    fresh_state: dict[str, Any],
    old_facts: dict[str, Any],
    new_facts: dict[str, Any],
    to_revision: dict[str, Any],
    from_source_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fact_delta = record_delta(old_facts.get("facts"), new_facts.get("facts"))
    relation_delta = record_delta(old_facts.get("relations"), new_facts.get("relations"))
    invalid_fact_ids = set(fact_delta["removedIds"]) | set(fact_delta["changedIds"])
    new_fact_ids = set(record_map(new_facts.get("facts")))
    retained_mappings = []
    stale_mapping_ids = []
    for mapping in old_state["mappings"]:
        references = set(mapping["codeFactIds"])
        if references <= new_fact_ids and not references & invalid_fact_ids:
            retained_mappings.append(deepcopy(mapping))
        else:
            stale_mapping_ids.append(mapping["id"])
    retained_work_ids = {mapping["workItemId"] for mapping in retained_mappings}
    work_items = deepcopy(old_state["workItems"])
    for work in work_items:
        retained = work["id"] in retained_work_ids
        work["status"] = "mapping-candidate" if retained else "intake"
        work["mappingStatus"] = "candidate" if retained else "unmapped"
        work["changeStatus"] = "not-proposed"
        work["verificationStatus"] = "snapshot-only"

    state = deepcopy(fresh_state)
    state["semanticFoundation"] = empty_semantic_foundation()
    state["semanticRelationOverlay"] = empty_semantic_relation_overlay()
    state["workItems"] = work_items
    state["mappings"] = retained_mappings
    state["changeProposals"] = []
    state["reviewReceipts"] = []
    state["verifierResults"] = []
    state["evidenceDecisions"] = []
    state["workStageRevisions"] = []
    state["verification"] = deepcopy(fresh_state["verification"])
    state["evidence"] = deepcopy(fresh_state["evidence"])
    state["history"] = deepcopy(fresh_state["history"])
    refresh_fragment = to_revision["id"].replace("revision.", "")
    state["verification"].append(
        {
            "id": f"verification.source-refresh.{refresh_fragment}",
            "kind": "source-refresh-integrity",
            "result": "pass",
            "summary": "The accepted source refresh candidate validated against a new immutable C# snapshot.",
            "factCount": len(record_map(new_facts.get("facts"))),
            "relationCount": len(record_map(new_facts.get("relations"))),
        }
    )
    state["evidence"].append(
        {
            "id": f"evidence.source-refresh.{refresh_fragment}",
            "kind": "source-refresh-receipt",
            "result": "pass",
            "summary": (
                f"Preserved revision {to_revision['sequence'] - 1} and accepted a reviewed "
                f"snapshot transition from {from_source_digest}."
            ),
        }
    )
    state["history"].append(
        {
            "id": f"history.source-refresh.{refresh_fragment}",
            "kind": "source-refresh-accepted",
            "summary": (
                "Activated a reviewed source snapshot; stale mappings and all snapshot-bound "
                "proposals were removed from the active revision and retained in the archived revision."
            ),
        }
    )
    invalidation = {
        "retainedMappingIds": sorted(mapping["id"] for mapping in retained_mappings),
        "staleMappingIds": sorted(stale_mapping_ids),
        "staleProposalIds": sorted(record["id"] for record in old_state["changeProposals"]),
        "staleReviewReceiptIds": sorted(record["id"] for record in old_state["reviewReceipts"]),
        "staleVerifierResultIds": sorted(record["id"] for record in old_state["verifierResults"]),
        "staleEvidenceDecisionIds": sorted(record["id"] for record in old_state["evidenceDecisions"]),
        "semanticRelationOverlayInvalidated": old_state.get("semanticRelationOverlay", {}).get("status") == "recorded",
        "semanticFoundationInvalidated": (
            old_state.get("semanticFoundation", empty_semantic_foundation()) != empty_semantic_foundation()
        ),
        "workStageRevisionCountArchived": len(old_state["workStageRevisions"]),
        "priorVerificationRecordCountArchived": len(old_state["verification"]),
        "priorEvidenceRecordCountArchived": len(old_state["evidence"]),
        "priorHistoryRecordCountArchived": len(old_state["history"]),
    }
    return state, {"facts": fact_delta, "relations": relation_delta, "invalidation": invalidation}


def recompute_plan_fields(
    prior_workspace: Path,
    current_workspace: Path,
    to_revision: dict[str, Any],
    from_source_digest: str,
) -> dict[str, Any]:
    old_state, _, old_snapshot_artifacts, old_data = validate_project_workspace(prior_workspace)
    current_state, current_manifest, current_snapshot_artifacts, current_data = validate_project_workspace(current_workspace)
    fresh_state = state_for(
        old_state["project"]["id"],
        old_state["project"]["title"],
        current_manifest,
        current_data["summary"],
    )
    expected_state, delta = candidate_state(
        old_state,
        fresh_state,
        old_data["facts"],
        current_data["facts"],
        to_revision,
        from_source_digest,
    )
    return {
        "candidateState": expected_state,
        "currentState": current_state,
        "sourceDelta": file_delta(
            csharp_source_records(old_snapshot_artifacts["sourceRoot"]),
            csharp_source_records(current_snapshot_artifacts["sourceRoot"]),
        ),
        "codeFactDelta": delta["facts"],
        "relationDelta": delta["relations"],
        "invalidation": delta["invalidation"],
        "preservation": {
            "priorWorkspaceSealedOnAcceptance": True,
            "priorHistoryRecordCount": len(old_state["history"]),
            "priorEvidenceRecordCount": len(old_state["evidence"]),
            "priorAuthorityDigest": digest_bytes(canonical_bytes(old_state["authority"])),
            "workItemCount": len(old_state["workItems"]),
            "targetRepositoryMutation": False,
        },
    }
