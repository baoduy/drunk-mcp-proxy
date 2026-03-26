# How to Use SPEC-KIT

## Initialize and Verify

```bash
# 1. install
uv tool install specify-cli --force --from git+https://github.com/github/spec-kit.git

# 2. setup
specify init . --ai copilot

# 3. Check installed tools
specify check
```

## Agent Folder Security

Some agents may store credentials, auth tokens, or other private artifacts in the agent folder within your project.

Consider adding `.github/` (or parts of it) to `.gitignore` to prevent accidental credential leakage.

## Next Steps

1. You are already in the project directory.
2. Start using slash commands with your AI agent:
    1. `/speckit.constitution` - Establish project principles
    2. `/speckit.specify` - Create baseline specification
    3. `/speckit.plan` - Create implementation plan
    4. `/speckit.tasks` - Generate actionable tasks
    5. `/speckit.implement` - Execute implementation

## Enhancement Commands

Optional commands to improve quality and confidence:

- `/speckit.clarify` (optional) - Ask structured questions to de-risk ambiguous areas before planning (run before `/speckit.plan` if used)
- `/speckit.analyze` (optional) - Cross-artifact consistency and alignment report (after `/speckit.tasks`, before `/speckit.implement`)
- `/speckit.checklist` (optional) - Generate quality checklists to validate requirements completeness, clarity, and consistency (after `/speckit.plan`)

## Constitution Quality Gates

Once `/speckit.constitution` is established, ensure each feature flow captures:

1. Class-first OOP boundaries and dependency injection decisions.
2. Security impact (input validation, error sanitization, secret-safe logging).
3. Test evidence for behavior changes (failing-first then passing).
4. Config and composition impacts (YAML/env/provider wiring).
5. Traceability updates (`CHANGE_LOGS.md` under `Unreleased` and related docs).
