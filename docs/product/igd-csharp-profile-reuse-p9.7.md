# P9.7 C# Profile Reuse and Dependency Boundary Gate

P9.7 decides what P9.6 proves and, equally importantly, what it does not prove.

## Evidence Considered

P9.6 used a disposable `net8.0` probe to parse WindowsUtility source with host SDK Roslyn binaries. The local machine has SDKs `8.0.100`, `8.0.404`, and `9.0.100`; no `global.json` pins a chosen SDK. The resulting whole-tree facts are deterministic, but the adapter path is derived from the active SDK host.

That is sufficient feasibility evidence. It is not sufficient evidence for a portable dependency, a supported installation contract, an offline distribution, a security-update policy, or broad C# profile support.

## Options

| Option | Decision | Reason |
|---|---|---|
| Use host-SDK Roslyn as a limited experimental local adapter | selected only for preflight | It reuses the proven local mechanism without adding a package, network, or target mutation. Its environment dependency remains visible. |
| Add a pinned Roslyn package to IGD | deferred | Requires version selection, license/security review, lock/restore/offline strategy, distribution policy, and clean-environment evidence. |
| Replace Roslyn immediately with another parser | deferred | No P9.6 failure requires a replacement; a different parser would require a new prior-art and extraction-quality comparison. |
| Stop at benchmark-only extraction | rejected for the next narrow step | It would prevent IGD from making the host dependency explicit and diagnosable, but remains the fallback if preflight is not reliable. |

## P9.7 Decision

P9.8 may implement only an `experimental-host-sdk` C# profile availability preflight. It is a local diagnostic, not a reusable extraction command or distribution feature.

The preflight may inspect local SDK metadata and the two required Roslyn binary paths. It must emit a deterministic report that names a logical profile identifier and availability result without reading WindowsUtility source, building a target, installing packages, restoring dependencies, calling the network, or using credentials.

The preflight must fail closed if there is no matching host SDK or either Roslyn binary is absent. It must label the result as environment-specific and experimental. It must not claim C# language-general support, portable packaging, semantic resolution, source mutation, or IGD product readiness.

## Deferred Decisions

Before a pinned Roslyn package or supported installation is introduced, a separate gate must decide:

- exact dependency/version and compatibility matrix
- license and security-update ownership
- package lock, offline cache, and clean-install behavior
- supported operating systems and SDK/runtime matrix
- adapter upgrade and rollback strategy
- package provenance and release authority

## Next Slice

`P9.8 Experimental Host-SDK C# Profile Availability Preflight` may be implemented after this plan. It must remain report-only and local-only.
