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


def verify(mapping_path: Path, target_root: Path):
    mapping_record = load_json(mapping_path)
    errors = []

    if mapping_record.get("artifactRole") != "intentgraph-windowsutility-accepted-mapping":
        errors.append("wrong artifactRole")
    if mapping_record.get("status") != "intentgraph-windowsutility-accepted-mapping-recorded":
        errors.append("wrong status")

    target = mapping_record.get("target", {})
    human = mapping_record.get("humanAcceptance", {})
    accepted = mapping_record.get("acceptedMapping", {})
    authorizations = mapping_record.get("authorizations", {})

    if target.get("baselineStatus") != "clean-aligned":
        errors.append("target baseline must be clean-aligned")
    if target.get("head") != target.get("originMain"):
        errors.append("target head must match originMain")
    if target.get("targetWritesAuthorized") is not False:
        errors.append("target writes must remain unauthorized")

    if human.get("recorded") is not True or human.get("accepted") is not True:
        errors.append("human acceptance must be recorded and accepted")
    if human.get("responseText") != "accept":
        errors.append("human acceptance response must be accept")

    if accepted.get("accepted") is not True:
        errors.append("accepted mapping must be accepted true")
    if accepted.get("mappingStatus") != "accepted":
        errors.append("accepted mapping status must be accepted")
    if accepted.get("sourceTextEqualityRequired") is not False:
        errors.append("source text equality must not be required")
    if accepted.get("hiddenGeneratedCodeSnapshotUsed") is not False:
        errors.append("hidden generated-code snapshot must not be used")

    if authorizations.get("acceptedMappingCreated") is not True:
        errors.append("acceptedMappingCreated must be true")
    for key in [
        "targetWritesAuthorized",
        "proposalApplicationAuthorized",
        "aiAuthorityPromoted",
        "productizationAuthorized",
    ]:
        if authorizations.get(key) is not False:
            errors.append(f"{key} must remain false")

    ref_results = []
    for ref in accepted.get("codeSurfaceRefs", []):
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
        if actual_digest != ref.get("digest"):
            errors.append(f"digest mismatch for source ref: {rel}")
        if actual_length != ref.get("byteLength"):
            errors.append(f"byte length mismatch for source ref: {rel}")
        ref_results.append(
            {
                "path": rel,
                "result": "checked",
                "actualDigest": actual_digest,
                "actualByteLength": actual_length,
            }
        )

    if not accepted.get("codeSurfaceRefs"):
        errors.append("accepted mapping must include codeSurfaceRefs")

    return {
        "artifactRole": "intentgraph-windowsutility-accepted-mapping-verification-report",
        "status": "intentgraph-windowsutility-accepted-mapping-verification-passed" if not errors else "intentgraph-windowsutility-accepted-mapping-verification-failed",
        "scope": "p8.9-shell-workspace-accepted-mapping-verification-report-only",
        "mapping": str(mapping_path).replace("\\", "/"),
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
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = verify(Path(args.mapping), Path(args.target_root))
    write_json(Path(args.out), report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
