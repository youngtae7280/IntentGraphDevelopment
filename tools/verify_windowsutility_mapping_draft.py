import argparse
import hashlib
import json
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def require_false(errors, value, message: str) -> None:
    if value is not False:
        errors.append(message)


def verify(draft_path: Path, target_root: Path):
    draft = load_json(draft_path)
    errors = []

    if draft.get("artifactRole") != "intentgraph-windowsutility-accepted-mapping-draft":
        errors.append("wrong artifactRole")
    if draft.get("status") != "intentgraph-windowsutility-accepted-mapping-draft-created":
        errors.append("wrong status")

    target = draft.get("target", {})
    mapping = draft.get("draftMapping", {})
    authorizations = draft.get("authorizations", {})

    require_false(errors, target.get("baselineAccepted"), "target baseline must remain unaccepted")
    require_false(errors, target.get("targetWritesAuthorized"), "target writes must remain unauthorized")
    require_false(errors, mapping.get("accepted"), "mapping draft must remain unaccepted")
    require_false(errors, mapping.get("sourceTextEqualityRequired"), "source text equality must not be required")
    require_false(errors, mapping.get("hiddenGeneratedCodeSnapshotUsed"), "hidden generated-code snapshot must not be used")

    for key in [
        "acceptedMappingCreated",
        "targetWritesAuthorized",
        "proposalApplicationAuthorized",
        "aiAuthorityPromoted",
        "productizationAuthorized",
    ]:
        require_false(errors, authorizations.get(key), f"{key} must remain false")

    ref_results = []
    for ref in mapping.get("codeSurfaceRefs", []):
        rel = ref.get("path")
        if not rel or Path(rel).is_absolute():
            errors.append(f"invalid relative source ref: {rel!r}")
            continue
        source_path = target_root / rel
        if not source_path.exists():
            errors.append(f"source ref missing: {rel}")
            ref_results.append({"path": rel, "result": "missing"})
            continue
        actual_digest = sha256_file(source_path)
        actual_length = source_path.stat().st_size
        expected_digest = ref.get("digest")
        expected_length = ref.get("byteLength")
        if actual_digest != expected_digest:
            errors.append(f"digest mismatch for source ref: {rel}")
        if actual_length != expected_length:
            errors.append(f"byte length mismatch for source ref: {rel}")
        if ref.get("refResolvedReadOnly") is not True:
            errors.append(f"source ref must be marked read-only resolved: {rel}")
        ref_results.append(
            {
                "path": rel,
                "result": "checked",
                "actualDigest": actual_digest,
                "actualByteLength": actual_length,
            }
        )

    if not mapping.get("codeSurfaceRefs"):
        errors.append("mapping draft must include codeSurfaceRefs")
    if not mapping.get("requiredBeforeAcceptance"):
        errors.append("mapping draft must list requiredBeforeAcceptance")

    return {
        "artifactRole": "intentgraph-windowsutility-mapping-draft-verification-report",
        "status": "intentgraph-windowsutility-mapping-draft-verification-passed" if not errors else "intentgraph-windowsutility-mapping-draft-verification-failed",
        "scope": "windowsutility-mapping-draft-verification-report-only",
        "draft": str(draft_path).replace("\\", "/"),
        "targetRoot": str(target_root),
        "result": "pass" if not errors else "fail",
        "errors": errors,
        "sourceRefResults": ref_results,
        "authorizations": {
            "acceptedMappingCreated": authorizations.get("acceptedMappingCreated"),
            "targetWritesAuthorized": authorizations.get("targetWritesAuthorized"),
            "proposalApplicationAuthorized": authorizations.get("proposalApplicationAuthorized"),
            "aiAuthorityPromoted": authorizations.get("aiAuthorityPromoted"),
            "productizationAuthorized": authorizations.get("productizationAuthorized"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = verify(Path(args.draft), Path(args.target_root))
    write_json(Path(args.out), report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
