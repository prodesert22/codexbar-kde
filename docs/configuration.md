# Configuration

## Files

| File | Purpose | Managed by |
| --- | --- | --- |
| `~/.codexbar/config.json` | Provider list, tokens, secrets | CodexBar app/CLI |
| `~/.config/codexbar-kde/state.json` | Widget preferences | Widget Settings UI |
| `~/.cache/codexbar-kde/last.json` | Last-good provider cache | Widget (auto) |

## state.json

All widget settings live here. Edit via Settings UI, or directly:

```json
{
  "barProvider": "",
  "refreshIntervalSeconds": "30",
  "allAccounts": "true",
  "statusPages": "false",
  "noCredits": "false",
  "showBarText": "true",
  "showAccountEmail": "true",
  "providerOrder": "[\"gemini\",\"codex\",\"claude\"]",
  "account:codex": "",
  "account:claude": "",
  "source:codex": "",
  "source:claude": ""
}
```

### Keys

| Key | Default | Values | Description |
| --- | --- | --- | --- |
| `barProvider` | `""` | provider id | Pin one provider to the panel bar. Empty = show highest-usage provider. |
| `refreshIntervalSeconds` | `"30"` | 10–600 | Seconds between auto-refreshes. |
| `allAccounts` | `"true"` | `"true"` / `"false"` | Pass `--all-accounts` to the CLI. |
| `statusPages` | `"false"` | `"true"` / `"false"` | Pass `--status` to fetch provider status pages. May cause errors with some providers (e.g., Claude). |
| `noCredits` | `"false"` | `"true"` / `"false"` | Pass `--no-credits` to hide Codex credit balance. |
| `showBarText` | `"true"` | `"true"` / `"false"` | Show usage percentage next to the icon in the panel bar. |
| `showAccountEmail` | `"true"` | `"true"` / `"false"` | Show account email below provider name in popup. When off, only the plan/org is shown. |
| `providerOrder` | `"[]"` | JSON array | Provider display order. Managed via drag-to-reorder in Settings. Example: `["gemini","codex","claude"]`. Unlisted providers appear last. |
| `account:<id>` | `""` | account label/email | Per-provider account filter. Passes `--account <value>` to CLI. Leave empty for all accounts. |
| `source:<id>` | `""` | `auto` / `oauth` / `cli` / `api` | Per-provider source override. `auto` and empty use widget defaults (oauth→cli for Claude, oauth for Codex). |

### CLI

```bash
python3 package/contents/code/codexbar_kde.py state           # read
python3 package/contents/code/codexbar_kde.py set-state \
  --key refreshIntervalSeconds --value 60                     # write single key
python3 package/contents/code/codexbar_kde.py batch-set-state \
  --json '[["refreshIntervalSeconds","60"],["showBarText","false"]]'  # write multiple keys at once
```

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `CODEXBAR_BIN` | auto | Path to the `codexbar` CLI binary. Detected from PATH, `/usr/bin/codexbar`, `/usr/local/bin/codexbar`, or `~/.local/bin/codexbar`. |
| `CODEXBAR_PROVIDERS` | from config | Space-separated provider IDs. Overrides config file. |
| `CODEXBAR_STAGGER` | `0.5` | Seconds between each provider fetch. |
| `CODEXBAR_ALL_ACCOUNTS` | `1` | Used when state `allAccounts` is true. Set to `0` to override. |
| `CODEXBAR_ANTIGRAVITY_CREDS` | `~/.gemini/oauth_creds.json` | Antigravity OAuth bridge file path. |
| `CODEXBAR_HELPER_MOCK_DIR` | — | Directory with `<provider>.json` mock files for testing. |

## Helper Commands

```bash
python3 package/contents/code/codexbar_kde.py summary        # fetch usage → JSON
python3 package/contents/code/codexbar_kde.py cache          # last-good cache → JSON
python3 package/contents/code/codexbar_kde.py settings       # settings payload → JSON
python3 package/contents/code/codexbar_kde.py cost           # cost/spend data → JSON
python3 package/contents/code/codexbar_kde.py cache-clear    # clear all caches
python3 package/contents/code/codexbar_kde.py providers      # enabled provider IDs
python3 package/contents/code/codexbar_kde.py state          # state.json → JSON
python3 package/contents/code/codexbar_kde.py set-state \
  --key <key> --value <value>                                 # update state.json
python3 package/contents/code/codexbar_kde.py batch-set-state \
  --json '[["key1","value1"],["key2","value2"]]'               # atomic multi-key update
```

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Widget shows `⚠` | Run `summary` command above and check the error. |
| `Plasma5Support.DataSource is not a type` | Install `plasma5support` package. |
| Icon shows `?` | Re-run `./install.sh`, restart Plasma. |
| `codexbar` not found | Install CLI or set `CODEXBAR_BIN`. |
| OpenCode/OpenCode Go missing | macOS-only web source; hidden on Linux but shown in Settings. |
| Wrong Codex account | `codex login` to switch, then refresh. |
| Claude "no token" error | Clear `source:claude` in state, clear cache in Settings, run `claude /login`. |
| Values are stale | Clear cache in Settings, or delete `~/.cache/codexbar-kde/last.json`. |
| Settings providers disappear | Clicking toggles should not hide the list. If it happens, close and reopen the popup. |
