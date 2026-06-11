# Changelog

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
