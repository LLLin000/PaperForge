# Release Acceptance

How PaperForge decides a candidate is fit to ship: what is tested, what the evidence means, and what separates "ready to publish" from "published".

## Language

**Acceptance Case**:
A planned, addressable unit of user-observable behavior in the acceptance matrix, identified like `B02` or `X05`.
_Not_: a test. A test is evidence for a case; one case may need several tests and several layers. _Avoid_: test case, scenario, ticket.

**Case Variant**:
One required branch of an Acceptance Case — a success, refusal, failure, cancellation, or persistence path that must be proven separately.
_Avoid_: treating one green path as the whole case.

**Evidence Layer**:
The classification of what actually ran for a case variant: `U` behavior/unit, `I` real process integration, `H` real Obsidian host, `V` live external service, `Q` human-ground-truth quality, `P` clean-environment published artifact.
_Avoid_: calling a `U` result end-to-end, or a stubbed provider `H`.

**Acceptance Evidence**:
The recorded result of running one case variant at one layer in one environment: `case_id + variant + required_layer + environment`.
_Avoid_: one boolean per case; re-labelling an old run's SHA as a new binding.

**Work Package**:
A dependency-ordered group of Acceptance Cases (`W01`–`W23`) that becomes one tracker issue; implementation issues are split from it when it starts.
_Avoid_: pre-creating implementation issues before the package starts.

**Candidate**:
The exact artifact set certification binds to: source SHA, plugin bundle, Python wheel, and configuration/fixture hashes.
_Avoid_: a branch name, a working tree, or "latest master".

**Certification**:
The final run that binds every applicable case variant to one Candidate and produces the result matrix.
_Avoid_: using development-time green runs as certification.

**RELEASE_READY**:
The pre-release business set is verified, certification is complete, and the owner has accepted the evidence. It is a precondition for publishing, never the authorization itself.
_Avoid_: treating it as permission to tag or publish.

**RELEASED**:
The owner authorized a specific version and artifact hashes, the single publish chain completed, and post-release smoke passed.
_Avoid_: equating a green pipeline with a completed release.

**Release-N**:
The previously published release that existing users upgrade from; its package and its support window bound upgrade/rollback acceptance.
_Avoid_: an unversioned "old version" or a hand-written legacy fixture claiming to be it.

**Blocking Gate**:
A `G01`–`G12` condition that must hold for RELEASE_READY; any unmet gate keeps the release at No-Go.
_Avoid_: a checklist item that can be waived by prose.

**Canary**:
An owner-authorized, small-scope production exposure used to observe real behavior after tests pass.
_Not_: a test stage, and not authorized by passing tests. _Avoid_: using "canary" for a sandbox or fixture run.
