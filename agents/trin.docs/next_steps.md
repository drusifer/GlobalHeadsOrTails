# Trin — Next Steps

1. UAT neo's session changes against PRD §13.9 exit criteria
2. Fix Playwright test ARM timeout — options:
   a. Add `@pytest.mark.slow` + skip by default in pyproject.toml
   b. Add `make test_sw` target in Makefile.prj with higher timeout
   c. Run on non-ARM machine
3. Re-UAT yield flow end-to-end (end_condition='yield' in DB, fanfare shows correct text)

*Last updated: 2026-03-26*
