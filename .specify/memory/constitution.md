<!--
Sync Impact Report
- Version change: 0.0.0 -> 1.0.0
- Modified principles:
	- PRINCIPLE_1_NAME -> I. Class-First OOP Architecture
	- PRINCIPLE_2_NAME -> II. Security-First and Safe Error Handling
	- PRINCIPLE_3_NAME -> III. Test-Backed Delivery (NON-NEGOTIABLE)
	- PRINCIPLE_4_NAME -> IV. Config-Driven Composition and Environment Control
	- PRINCIPLE_5_NAME -> V. Traceable Change Management
- Added sections:
	- Engineering Standards and Constraints
	- Delivery Workflow and Quality Gates
- Removed sections: None
- Templates requiring updates:
	- ✅ updated: .specify/templates/plan-template.md
	- ✅ updated: .specify/templates/spec-template.md
	- ✅ updated: .specify/templates/tasks-template.md
	- ⚠ pending: .specify/templates/commands/*.md (directory not present in this repository)
	- ✅ updated: SPEC_KIT.md
- Deferred TODOs: None
-->

# Drunk MCP Proxy Constitution

## Core Principles

### I. Class-First OOP Architecture
All new or modified business logic MUST be implemented in class-first modules. Core orchestration
MUST live in class methods, not module-level procedural functions. Dependencies MUST be injected
through constructors, stored as private attributes, and typed explicitly. This rule exists to keep
modules cohesive, testable, and safe to refactor.

### II. Security-First and Safe Error Handling
All externally sourced data (headers, payloads, file paths, URLs, remote resources, prompt inputs)
MUST be validated before use. Returned errors MUST be sanitized. Logs MUST avoid secrets and MUST
log exception type rather than full exception payload when sensitive details could leak. Security
middleware and repository security utilities MUST be used instead of ad hoc implementations.

### III. Test-Backed Delivery (NON-NEGOTIABLE)
Behavioral changes MUST include or update automated tests that fail before the fix and pass after
implementation. At minimum, an affected-scope test command MUST be executed before merge, and full
suite execution SHOULD be run before release. A change without test evidence is incomplete unless
explicitly approved as documentation-only or non-runtime-only work.

### IV. Config-Driven Composition and Environment Control
Runtime behavior MUST be controlled by typed configuration and environment variables, not hardcoded
branching. Canonical project configuration is YAML using snake_case field names. Providers and
routes MUST be assembled from configuration at application composition boundaries to preserve
predictable deployment behavior across local, CI, and production environments.

### V. Traceable Change Management
Every code change MUST be traceable through updated specifications/tasks (when applicable),
documentation updates for behavior changes, and an entry in CHANGE_LOGS.md under Unreleased.
Versioned governance and implementation artifacts MUST remain synchronized so delivery decisions
are auditable and reproducible.

## Engineering Standards and Constraints

- Python 3.10+ features are required, including modern type syntax (for example, X | Y and
	list[str]); legacy typing forms SHOULD be avoided unless required by a dependency boundary.
- Type hints are required on all function signatures and public method returns.
- Module-level logger usage MUST follow the shared repository pattern with safe logging behavior.
- FastAPI and Pydantic usage MUST follow current stable patterns used in this repository.
- Imports within project packages MUST follow repository import-root conventions.

## Delivery Workflow and Quality Gates

- Non-trivial work MUST follow the specification workflow: constitution alignment, specification,
	implementation plan, and tasks before implementation.
- Pull requests MUST pass constitution checks in planning artifacts before coding begins.
- Pull requests MUST include: test evidence, security impact review, and changelog update.
- If architectural constraints are intentionally violated, the violation MUST be documented with
	rationale and an explicit simpler alternative considered.
- Reviewers MUST block merges that violate non-negotiable principles unless a documented temporary
	exception includes owner and removal date.

## Governance

This constitution is the highest-priority engineering policy for this repository. In case of
conflict, this constitution supersedes workflow notes, prompts, and local conventions.

Amendment procedure:
1. Propose amendment with explicit rationale and impacted principles/sections.
2. Update dependent templates and guidance documents in the same change.
3. Include a Sync Impact Report in the constitution update.
4. Obtain maintainer approval before merge.

Versioning policy:
- MAJOR: breaking governance change, principle removal, or principle redefinition.
- MINOR: new principle/section or materially expanded mandatory guidance.
- PATCH: clarifications, wording refinements, or typo-level non-semantic edits.

Compliance review expectations:
- Every plan MUST include a Constitution Check gate before research and after design.
- Every task list MUST carry constitution-driven tasks for tests, security, and changelog work.
- Every implementation review MUST verify constitution compliance explicitly.

**Version**: 1.0.0 | **Ratified**: 2026-03-26 | **Last Amended**: 2026-03-26
