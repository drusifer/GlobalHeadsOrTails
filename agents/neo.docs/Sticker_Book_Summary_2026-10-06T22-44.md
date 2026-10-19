# Sticker Book UI update

Sticker Book now lives in the bottom tab group beside Recent Flips and Leaderboard. Current-season narrative is visible by default inside the tab. Only currently owned forms for the tapped coin render; no tap renders no stickers. Drop notices and wager actions remain outside tabs. Mobile browser acceptance passes, including no-tap description, tab switching, owned forms, evolution and wagers; syntax checks and git diff --check pass. Use CHROMIUM_PATH=/usr/bin/chromium make -C ntag424_sdm_provisioner test_sticker_ui on this machine.
