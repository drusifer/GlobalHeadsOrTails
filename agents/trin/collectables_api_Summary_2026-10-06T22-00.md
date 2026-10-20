# Collectables independent QA
Result: 107 server tests passed.
Added 22 API regressions covering signed taps, duplicate replay and UID casing, invalid/test exclusion, wager auth/ownership/forgery, accepted yield exactly-once, concurrent same-counter request, migration, malformed JSON and compact payloads. Injected interruption proves scan/drop/progress rollback. Accepted wager completes through real API taps; final uncommitted HEADS changes winner from draw to A.
Service changes: borrowed transaction award/progress seams, same-connection entropy snapshot, cached catalog and compact inventory, persisted terminal evolution events and migration, optional expired latest challenge lookup.
Root fixed application transaction integration and malformed payload/UID normalization findings. Browser and artwork reviewed separately by root/Smith.
