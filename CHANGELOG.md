# Changelog

## 0.2.0 (2026-06-12)

### Added
- Version info footer on the Settings page showing the plasmoid version
  (`codexbarkde`) and the CodexBar CLI version (`codexbar --version`).

### Fixed
- Settings changes now apply instantly on OK/Apply instead of waiting for a
  slow network refetch. Display-only toggles (show bar text, show account
  email) update `root.settings` locally; pinning and provider reordering use
  a fast local cache recompute; only `allAccounts`/`statusPages`/`noCredits`
  trigger a network refetch.
- Toggling "show bar text" no longer takes effect before OK/Apply — pending
  changes stay pending and the live bar is untouched until applied.
- Compact panel widget now resizes with its content (`Layout.minimum/maximumWidth`
  bound to `implicitWidth`), fixing the clipped icon and cut-off text when the
  bar text was toggled on.
- Closing the popup now returns to the usage page; reopening no longer lands on
  the Settings page, and uncommitted settings changes are discarded.

## 0.1.2 (2026-06-11)

### Added
- GitHub Actions CI (`.github/workflows/ci.yml`): runs on push/PR to `master`.
  - `tests` job — matrix over Python 3.10–3.13 (parallel jobs), each running
    `pytest -n auto` to parallelize test methods across CPU cores.
  - `qmllint` job — Qt6 QML syntax/structure check.
- `requirements-dev.txt` — test-only dev deps (`pytest`, `pytest-xdist`).
  Runtime helper stays stdlib-only.

### Changed
- `scripts/test.sh` now prefers `pytest -n auto` for parallel runs, falling
  back to stdlib `unittest` when pytest is not installed.

## 0.1.1 (2026-06-11)

### Fixed
- Deduplicated `compactLabel` percentage extraction into `compactLabelPct()` function
- `settingsOk()` now delegates to `settingsApply()` instead of duplicating logic
- Removed redundant `Layout.preferredWidth: implicitWidth` on compact bar
- Provider status indicator deduplicated via `statusIndicator` property
- Fragile codexbar binary test now skips gracefully when CLI not installed
- Indentation normalized after QML file split

### Changed
- `main.qml` split into 5 focused files: `FullPopup.qml`, `SettingsPage.qml`, `UsagePage.qml`, `UsageBar.qml`

## 0.1.0 (2026-06-11)

Initial release.

### Features
- Panel icon with usage percentage (color-coded: blue < 70%, yellow < 90%, red ≥ 90%)
- Click popup with per-provider usage bars (session, weekly, monthly)
- Account identity display (email, plan/org, login method)
- Cost/spend data via chart button
- Provider status indicators (green/yellow/red dot)
- Provider pinning to panel bar
- Drag-to-reorder providers in settings
- Settings: enable/disable providers, source overrides, account selection
- Settings: refresh interval, all-accounts toggle, status pages, hide credits, show/hide bar text
- Settings: show/hide account email (keeps plan visible when off)
- Batch state persistence (OK/Apply/Cancel with dirty tracking)
- Cache clearing
- Compact bar text toggle
- Claude OAuth → CLI fallback chain
- `codexbar` CLI auto-detection with `CODEXBAR_BIN` env override
- Search/filter providers in settings
- `.gitignore`, `VERSION`, and `CHANGELOG.md`
