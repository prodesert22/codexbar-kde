# Development

## Project layout

```text
./
├── package/                     # Plasmoid package
│   ├── metadata.json            # KDE plugin metadata
│   └── contents/
│       ├── code/
│       │   └── codexbar_kde.py  # Python data helper (all logic)
│       ├── images/
│       │   └── codexbar.png     # Widget icon
│       └── ui/
│           ├── main.qml         # Shell (properties, functions, compact bar)
│           ├── FullPopup.qml    # Popup orchestrator (header, pages, footer)
│           ├── SettingsPage.qml  # Settings scroll view (toggles, search, provider list)
│           ├── UsagePage.qml    # Usage view (provider cards, bars, cost)
│           └── UsageBar.qml     # Usage progress bar component
├── docs/                        # Documentation
│   ├── configuration.md
│   ├── accounts.md
│   └── development.md
├── tests/
│   └── test_codexbar_kde.py     # Python unit tests
├── scripts/
│   └── test.sh                  # Test runner (Python + QML lint)
├── install.sh                   # Installer script
├── LICENSE                      # MIT
├── assets/                      # Screenshots
│   ├── codexbar-kde.png
│   ├── panelbar.png
│   └── settings.png
└── README.md
```

## Architecture

The widget has two layers:

1. **QML UI** — 5 files split by responsibility:
   - `main.qml` — PlasmoidItem shell: properties, JS functions, Timer, DataSource, compact bar
   - `FullPopup.qml` — popup header, error area, switches between settings/usage pages
   - `SettingsPage.qml` — settings scroll view (toggles, provider order, search, provider delegates)
   - `UsagePage.qml` — usage view (provider cards with usage bars, cost, status)
   - `UsageBar.qml` — reusable progress bar component

2. **Python helper** (`codexbar_kde.py`) — all data logic: calling `codexbar` CLI, parsing JSON, caching, state management. This is the testable layer.

Separation keeps QML simple and makes the logic testable without KDE.

## Running tests

```bash
./scripts/test.sh
```

This runs:
- Python unit tests (`python3 -m unittest`)
- QML lint (`qmllint`)

### Adding tests

Tests go in `tests/test_codexbar_kde.py`. They use `importlib` to load the helper module directly.

Tests are isolated from the real `state.json` via `setUp`/`tearDown` that mock `state_value` and `state_full` with in-memory dicts.

```python
def setUp(self):
    self._state = {}
    setattr(helper, "state_value", lambda key="", default="": self._state.get(key, default))
```

## Helper commands

All helper commands return JSON to stdout (except `set-state` which is silent on success).

| Command | Output | Description |
| --- | --- | --- |
| `summary` | usage JSON | Fetches all enabled providers |
| `cache` | usage JSON | Returns last-good cache without fetching |
| `settings` | settings JSON | Provider list + all state values |
| `cost` | cost JSON | `codexbar cost` output |
| `cache-clear` | `{}` | Clears CodexBar caches + last-good |
| `providers` | id list | Enabled provider IDs |
| `state` | state JSON | Raw state.json contents |
| `set-state --key X --value Y` | — | Updates a state key |
| `batch-set-state --json '[[k,v],...]'` | — | Atomic multi-key state update |

## Testing without KDE

You can test the helper directly:

```bash
python3 package/contents/code/codexbar_kde.py summary
```

Or with mock provider data:

```bash
mkdir -p /tmp/codexbar-mock
echo '[{"provider":"codex","usage":{"primary":{"usedPercent":42}}}]' > /tmp/codexbar-mock/codex.json
CODEXBAR_PROVIDERS=codex CODEXBAR_HELPER_MOCK_DIR=/tmp/codexbar-mock \
  python3 package/contents/code/codexbar_kde.py summary
```

## Testing with KDE

If you have Plasma SDK installed:

```bash
plasmoidviewer package -l topedge -f horizontal
plasmawindowed dev.codexbar.kde
```

## Install during development

```bash
./install.sh
```

This runs `kpackagetool6 -t Plasma/Applet -u package` (update) or `-i` (install). Restart Plasma to pick up changes:

```bash
systemctl --user restart plasma-plasmashell
```

Or remove and re-add the widget from the panel.
