# Test-tap stickers

User rejected separate simulator; removed its script and Makefile targets. Existing drew_test_outcome=heads/tails now awards stickers to selected coin using normal 50% odds and auto evolution. Invalid outcomes never award. Test UID/counter ledger is namespaced to avoid consuming real signed-tap awards; repeated test counter does not reroll. Increment hexadecimal ctr for new test drops. 110 server tests and syntax checks pass.
