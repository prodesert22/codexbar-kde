# CodexBar KDE — Agent Guidelines

## Project

KDE Plasma 6 panel widget (plasmoid) that shows CodexBar AI provider usage.
Python data helper + QML UI, packaged for `kpackagetool6`.

## Project Structure

```
package/
  metadata.json
  contents/
    code/
      codexbar_kde.py         # Python helper (CLI, state, caching)
    images/
      codexbar.png            # Widget icon
    ui/
      main.qml                # PlasmoidItem shell (props, functions, compact bar)
      FullPopup.qml           # Popup orchestrator (header, pages, footer)
      SettingsPage.qml        # Settings (toggles, search, provider list, drag-reorder)
      UsagePage.qml           # Usage view (provider cards, bars, cost, status)
      UsageBar.qml            # Reusable progress bar
tests/
  test_codexbar_kde.py        # 28 unit tests
scripts/
  test.sh                     # python -m unittest + qmllint
docs/
  configuration.md            # State file, env vars, troubleshooting
  development.md              # Architecture, testing, helper commands
install.sh                    # Installer (kpackagetool6)
VERSION                       # Semver (used by install.sh, future AUR PKGBUILD)
CHANGELOG.md
```

## State File Backward Compatibility

**`~/.config/codexbar-kde/state.json` must remain backward compatible.**

- Never remove a key. If a key becomes obsolete, keep reading it but ignore the value.
- Never rename a key. Add the new name and read both (old as fallback).
- Never change a key's type. `"true"`/`"false"` strings stay strings.
- New keys must have defaults. All `sf.get("key", "default")` calls must provide a sensible fallback.
- Unknown keys in the state file must be silently ignored — never crash on unexpected keys.
- The settings UI widget (QML) reads state keys; the Python helper writes them.

## Coding Conventions

### Python (`codexbar_kde.py`)
- No external dependencies beyond stdlib. The helper runs in the user's system Python.
- Warn and continue. Network errors, missing CLI, and unparseable JSON produce fallback data or error entries — never crash.
- Every function not called by `main()` must be tested.

### QML
- No hardcoded colors. Use `Kirigami.Theme.textColor`/`disabledTextColor`/`negativeTextColor` where possible. Provider-specific colors (`levelColor()`) are the exception.
- No hardcoded sizes. Use `Kirigami.Units.*` for spacing, icons, fonts.
- Every ID must be referenced somewhere. Remove vestigial `id:` declarations.
- Settings UI must not overflow. All text labels need `Layout.fillWidth: true`, `elide`, or `wrapMode`.
- Batch state writes via `saveStateKey()` → `flushPendingChanges()`. Never call the CLI per-toggle.

### Shell (`install.sh`, `scripts/test.sh`)
- `set -euo pipefail` in every script.
- Use `$DATA_HOME`/`$XDG_*` variables, not hardcoded paths.

## Adding a New Setting

When adding a toggle/field to the settings UI:

1. Add the key to `settings_payload()` in `codexbar_kde.py` with a default via `sf.get("key", "default")`.
2. Add the property to the `settings` default object in `main.qml`.
3. Add the UI control (Switch, SpinBox, ComboBox) in `SettingsPage.qml`.
4. Wire `onToggled`/`onChanged` to `root.saveStateKey("key", value)`.
5. If the setting changes which data is fetched, update `fetch_once()`/`summarize()` in Python.
6. Add a test for the new field in `test_codexbar_kde.py`.
7. Add the key to `docs/configuration.md`.

## Before Committing

```bash
./scripts/test.sh    # 28 tests + qmllint
```

All tests must pass. QML lint must be clean. Python syntax and logic must be verified.

## Installing

```bash
./install.sh    # Update or install the plasmoid
```

## Architecture Decision: Python + QML split

- **Python helper** handles all CLI interaction, JSON parsing, caching, and state persistence.
- **QML UI** is purely presentational. It calls the helper via `Plasma5Support.DataSource` with `engine: "executable"`.
- This split keeps the logic testable without KDE, and the UI free of shell/JSON logic.
