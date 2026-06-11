# Changelog

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
