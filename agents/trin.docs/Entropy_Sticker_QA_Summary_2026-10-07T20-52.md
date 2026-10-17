# Entropy sticker QA

Entropy sticker backend QA approved. All 126 server tests pass via make -C ntag424_sdm_provisioner test_collectables (4.31s). Five regressions added: actual99/100 monobit boundary, mature weighting symmetry/floor, signed two-face shared coin history and inventory, ignored client odds fields, legacy no-odds ledger replay through API. Initial test expected60/40 above floor; corrected to documented5% floor without production changes. Reviewed accepted Cypher policy; Oracle lessons/memory absent as documented. Root owns final browser gate and closure. No build/commit/deploy performed.


Final browser acceptance reported by root: extended mobile Chromium session51070 passes mature50%/p=1 odds display, test-mode label, genuine history stays100 after test tap, plus prior album/evolution/wager flows. No further tests required;126server regressions remain green. Full QA gate approved.
