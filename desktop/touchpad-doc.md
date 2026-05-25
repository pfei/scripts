# Summary: Touchpad Toggle Automation (Dell / MATE)

## 1. Initial Issues

Managing the touchpad toggle via raw Shell (`zsh`) scripts introduced
several brittle points:

1. **Unreliable Text Parsing:** Tools like `xinput` frequently failed due to
   hidden trailing spaces or unexpected carriage returns returned by Dell's
   ACPI drivers.
1. **Hardware Hardcoding:** Using unique hardware IDs (e.g., `DLL079F`) made
   scripts incompatible when moving from one Latitude laptop model to another.
1. **Environment Restrictions (MATE vs. Terminal):** MATE's global keyboard
   shortcut daemon executes commands within a minimal background environment.
   It lacks the user's custom `$PATH` and the `$DISPLAY` variable, causing
   local background execution to fail silently.

______________________________________________________________________

## 2. Solution Architecture

All scripts are centralized within your Git repository
(`~/src/scripts/desktop`) and deployed locally via symbolic links into
`~/.local/bin`.

```text
~/src/scripts/desktop/
├── install-symlinks.py       # Symlink automation script
├── toggle-touchpad.py         # Main script (Toggle logic)
└── toggle-touchpad-wrapper.py # Adaptor for the MATE environment
```

______________________________________________________________________

## 3. Technical Components

### A. The Main Script: `toggle-touchpad.py`

This script handles device detection and switches the state. It eliminates
parsing bugs by extracting the pure **numeric ID** of the device using a
universal regular expression tailored for Dell hardware.

- **Universal Dell Regex:** `(?:DELL\w+|DLL\w+|touchpad|glidepoint)`
  - Matches modern hardware tags (`DLLXXXX`, `DELLXXXX`) as well as older
    pointing devices (`touchpad`, `glidepoint`), ensuring compatibility
    across your entire laptop fleet.
- **ID Extraction:** Captures the raw integer ID (e.g., `10`), completely
  bypassing shell quoting and whitespace issues.

### B. The MATE Wrapper: `toggle-touchpad-wrapper.py`

Built specifically to address the missing environment variables when
triggered by a global desktop environment keystroke.

- **Role:** It explicitly injects the `DISPLAY=:0` environment variable
  required by X11, then safely triggers the main script execution.

### C. The Installer: `install-symlinks.py`

Automates the creation and override of symbolic links inside your local
binary folder:

- `~/.local/bin/toggle-touchpad` -> Points to the main script (for manual
  terminal usage).
- `~/.local/bin/toggle-touchpad-click` -> Points to the wrapper script (for
  MATE shortcut usage).

______________________________________________________________________

## 4. Keyboard Shortcut Configuration (MATE)

To bypass the fact that MATE's shortcut manager does not evaluate
`~/.local/bin` in its default `$PATH`, the keybinding for **F5** is mapped
using the **absolute path** of the wrapper's symlink.

- **Menu Path:** System -> Preferences -> Hardware -> Keyboard Shortcuts
- **Action Name:** `Toggle Touchpad`
- **Command:** `/home/pierre/.local/bin/toggle-touchpad-click`
- **Associated Key:** `F5` (Verified as free and active via `xev`)

______________________________________________________________________

## 5. Portability and Git Maintenance

The entire setup is modular, self-contained, and tracked in Git. To deploy
this feature on any other Dell machine in your fleet, the procedure is
straightforward:

```bash
# 1. Clone/update your scripts repository
cd ~/src/scripts

# 2. Run the installer to generate local symlinks
./desktop/install-symlinks.py

# 3. Map the F5 key to this absolute path in MATE's shortcut manager:
# /home/pierre/.local/bin/toggle-touchpad-click
```
