# Oracle Query: ChangeFileSettings Encryption Rules

**Context:**
I am implementing `ChangeFileSettings` in `change_file_settings.py`.
- `ChangeFileSettingsAuth` (authenticated version) currently returns `True` for `needs_encryption()`.
- The comment says: "ChangeFileSettings is ALWAYS sent encrypted (FULL mode)."
- I am verifying this against the Arduino reference `MFRC522_NTAG424DNA.cpp`.

**Question:**
Does the NTAG 424 DNA specification require `ChangeFileSettings` to *always* be encrypted (Full Mode), or is it possible to send it in MAC-only mode if the file's access rights allow it?
Specifically, if I am changing settings for a file that is currently in PLAIN mode, but the `Change` access right requires authentication (e.g., Key 0), must the command payload itself be encrypted?

**Reference Check:**
- `MFRC522_NTAG424DNA.cpp` line 986 `DNA_Full_ChangeFileSettings` seems to imply Full Mode.
- Is there a `DNA_Mac_ChangeFileSettings` equivalent?

**Goal:**
Ensure `change_file_settings.py` correctly implements the protocol and doesn't encrypt unnecessarily if MAC-only is sufficient, OR confirm that encryption is mandatory.
