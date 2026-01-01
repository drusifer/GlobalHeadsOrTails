# Bob - Current Context

**Last Updated**: 2025-11-30 12:00

## Recent Improvements
- State management system implemented
- Cross-persona command usage guidelines added
- **Ruff code quality guardrails added to all agents**
- conftest.py guard prevents test structure mistakes

## Prompt Updates Completed
- ✅ Bob_PE_AGENT.md - Ruff guardrails added
- ✅ Neo_SWE_AGENT.md - Ruff workflow integrated
- ✅ Trin_QA_AGENT.md - Quality gate with ruff checks
- ✅ Morpheus_SE_AGENT.md - Ruff enforcement authority

## System Health
- Oracle consultation: Improved
- Quality standards: Active
- Import standards: **Enforced via ruff TID252**
- Test structure: **Protected by conftest.py guard**

## Notes
All agents now have ruff guardrails. Key enforcement points:
- Neo runs `ruff check --fix` before committing
- Trin rejects code with ruff violations
- Morpheus has veto power on violations
