#!/usr/bin/env python3
"""Small data helper for the CodexBar KDE Plasma widget.

The Plasma UI stays simple QML. This helper owns all JSON, CLI, cache and
formatting logic so it can be tested without KDE running.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Any, Callable


DEFAULT_PROVIDERS = ["codex", "claude", "gemini"]
SOURCE_OVERRIDES = {"codex": "oauth", "claude": "oauth"}
FALLBACK_SOURCES = {"claude": "cli"}
LINUX_UNSUPPORTED_WEB_PROVIDERS = {"opencode", "opencodego"}
AVAILABLE_SOURCES: dict[str, list[str]] = {
    "codex": ["auto", "oauth", "cli"],
    "claude": ["auto", "oauth", "cli", "api"],
    "gemini": ["auto", "api"],
    "openai": ["auto", "api"],
    "copilot": ["auto", "api"],
    "openrouter": ["auto", "api"],
    "deepseek": ["auto", "api"],
    "vertexai": ["auto", "oauth", "api"],
    "antigravity": ["auto", "api"],
    "kilo": ["auto", "api", "cli"],
    "kiro": ["auto", "cli"],
    "kimik2": ["auto", "api"],
    "moonshot": ["auto", "api"],
    "minimax": ["auto", "api"],
    "venice": ["auto", "api"],
    "warp": ["auto", "api"],
    "zai": ["auto", "api"],
    "codebuff": ["auto", "api"],
    "crof": ["auto", "api"],
    "cursor": ["auto", "api"],
}
FALLBACK_AVAILABLE_SOURCES = ["auto"]
PROVIDER_NAMES = {
    "codex": "Codex",
    "claude": "Claude",
    "gemini": "Gemini",
    "copilot": "Copilot",
    "cursor": "Cursor",
    "openai": "OpenAI",
    "openrouter": "OpenRouter",
    "deepseek": "DeepSeek",
    "vertexai": "Vertex AI",
    "kimik2": "Kimi K2",
    "moonshot": "Moonshot",
    "antigravity": "Antigravity",
    "minimax": "MiniMax",
    "venice": "Venice",
    "warp": "Warp",
    "zai": "Z.ai",
    "kilo": "Kilo Code",
    "codebuff": "Codebuff",
    "crof": "Crof",
    "opencode": "OpenCode",
    "opencodego": "OpenCode Go",
}
WINDOW_LABELS = {"primary": "Session", "secondary": "Weekly", "tertiary": "Monthly"}


@dataclass(frozen=True)
class Paths:
    config: Path
    state: Path
    cache_dir: Path
    last_good: Path


def xdg_path(env_name: str, fallback: Path) -> Path:
    raw = os.environ.get(env_name)
    return Path(raw).expanduser() if raw else fallback


def paths() -> Paths:
    home = Path.home()
    config_home = xdg_path("XDG_CONFIG_HOME", home / ".config")
    cache_home = xdg_path("XDG_CACHE_HOME", home / ".cache")
    cache_dir = cache_home / "codexbar-kde"
    return Paths(
        config=home / ".codexbar" / "config.json",
        state=config_home / "codexbar-kde" / "state.json",
        cache_dir=cache_dir,
        last_good=cache_dir / "last.json",
    )


def load_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default
    except OSError:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
        fh.write("\n")
    tmp.replace(path)


def enabled_providers(config_path: Path | None = None, env: Mapping[str, str] | None = None) -> list[str]:
    env = env or os.environ
    override = env.get("CODEXBAR_PROVIDERS", "").strip()
    if override:
        return [p for p in override.split() if p]

    config_path = config_path or paths().config
    config = load_json(config_path, {})
    providers = []
    for item in config.get("providers", []) if isinstance(config, dict) else []:
        if isinstance(item, dict) and item.get("enabled") is True and item.get("id"):
            providers.append(str(item["id"]))
    return providers or list(DEFAULT_PROVIDERS)


def config_provider_items(config_path: Path | None = None) -> list[dict[str, Any]]:
    config = load_json(config_path or paths().config, {})
    items = config.get("providers", []) if isinstance(config, dict) else []
    return [item for item in items if isinstance(item, dict) and item.get("id")]


def provider_config_map(config_path: Path | None = None) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in config_provider_items(config_path)}


def _state_path(state_path: Path | None = None) -> Path:
    return state_path or paths().state


def state_full(state_path: Path | None = None) -> dict[str, Any]:
    state = load_json(_state_path(state_path), {})
    return state if isinstance(state, dict) else {}


def state_value(state_path: Path | None = None, key: str = "barProvider", default: str = "") -> str:
    state = state_full(state_path)
    value = state.get(key, default)
    return str(value) if value is not None else default


def _write_state(payload: dict[str, Any], state_path: Path | None = None) -> None:
    write_json(_state_path(state_path), payload)


def _provider_order() -> list[str]:
    raw = state_value(key="providerOrder", default="")
    if not raw:
        return []
    try:
        order = json.loads(raw)
        return [str(x) for x in order] if isinstance(order, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _sort_by_order(providers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = _provider_order()
    if not order:
        return providers
    ranked = []
    rest = []
    seen = set()
    for oid in order:
        for entry in providers:
            if entry.get("provider") == oid and oid not in seen:
                ranked.append(entry)
                seen.add(oid)
    for entry in providers:
        if entry.get("provider") not in seen:
            rest.append(entry)
    return ranked + rest


def source_options(provider_id: str) -> list[str]:
    return AVAILABLE_SOURCES.get(provider_id, list(FALLBACK_AVAILABLE_SOURCES))


Runner = Callable[[list[str], dict[str, str]], subprocess.CompletedProcess[str]]


def run_process(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, env=env, text=True, capture_output=True, timeout=45, check=False)
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=args,
            returncode=127,
            stdout="",
            stderr=(
                f"CodexBar CLI not found: {args[0]}\n\n"
                "Install it, or set CODEXBAR_BIN to the full path of your codexbar executable.\n"
                "If installed from AUR, it is usually /usr/bin/codexbar."
            ),
        )


def codexbar_binary(env: Mapping[str, str] | None = None) -> str:
    env = env or os.environ
    override = env.get("CODEXBAR_BIN")
    if override:
        return override

    found = which("codexbar", path=env.get("PATH"))
    if found:
        return found

    for candidate in (Path("/usr/bin/codexbar"), Path("/usr/local/bin/codexbar"), Path.home() / ".local/bin/codexbar"):
        if candidate.exists():
            return str(candidate)

    return str(Path.home() / ".local/bin/codexbar")


def antigravity_env(env: dict[str, str], provider: str) -> dict[str, str]:
    if provider != "antigravity" or env.get("ANTIGRAVITY_OAUTH_CREDENTIALS_JSON"):
        return env
    creds_path = Path(env.get("CODEXBAR_ANTIGRAVITY_CREDS", str(Path.home() / ".gemini/oauth_creds.json")))
    try:
        creds = creds_path.read_text(encoding="utf-8")
    except OSError:
        return env
    merged = dict(env)
    merged["ANTIGRAVITY_OAUTH_CREDENTIALS_JSON"] = creds
    return merged


def fetch_once(provider: str, source: str | None, runner: Runner = run_process, env: Mapping[str, str] | None = None, account: str | None = None) -> list[dict[str, Any]]:
    env = dict(env or os.environ)
    args = [codexbar_binary(env), "usage", "--provider", provider, "--format", "json", "--no-color"]
    if state_value(key="statusPages", default="false").lower() == "true":
        args.append("--status")
    if state_value(key="noCredits", default="false").lower() == "true":
        args.append("--no-credits")
    if account:
        args += ["--account", account]
    else:
        skip_all = source and source in {"oauth", "cli"} and provider == "claude"
        if not skip_all:
            use_all = state_value(key="allAccounts", default="true").lower() == "true"
            env_all = env.get("CODEXBAR_ALL_ACCOUNTS", "1")
            if use_all and env_all not in {"0", "false", "False"}:
                args.append("--all-accounts")
    if source:
        args += ["--source", source]
    proc = runner(args, antigravity_env(env, provider))
    if proc.returncode != 0 and not proc.stdout.strip():
        return [{"provider": provider, "error": {"message": (proc.stderr or "codexbar failed").strip()}}]
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return [{"provider": provider, "error": {"message": "invalid JSON from codexbar"}}]
    if not isinstance(data, list):
        return [{"provider": provider, "error": {"message": "unexpected codexbar JSON shape"}}]
    return [entry for entry in data if isinstance(entry, dict)]


def has_provider_error(entries: list[dict[str, Any]]) -> bool:
    return bool(entries) and all(bool(entry.get("error")) for entry in entries)


def fetch_provider(provider: str, runner: Runner = run_process, env: Mapping[str, str] | None = None, account: str | None = None) -> list[dict[str, Any]]:
    if sys.platform.startswith("linux") and provider in LINUX_UNSUPPORTED_WEB_PROVIDERS:
        return [{
            "provider": provider,
            "skipped": True,
            "warning": {
                "message": f"{provider_name(provider)} is hidden on Linux because the current CodexBar CLI only supports its web/local source on macOS."
            },
            "linuxUnsupported": True,
        }]

    user_source = state_value(key=f"source:{provider}")
    if user_source and user_source != "auto":
        primary = user_source
        fallback_enabled = False
    else:
        primary = SOURCE_OVERRIDES.get(provider)
        fallback_enabled = True
    entries = fetch_once(provider, primary, runner=runner, env=env, account=account)
    fallback = FALLBACK_SOURCES.get(provider)
    if fallback and has_provider_error(entries) and fallback_enabled:
        retry = fetch_once(provider, fallback, runner=runner, env=env, account=account)
        if retry:
            return retry
    return entries


def read_mock_provider(provider: str, mock_dir: Path) -> list[dict[str, Any]] | None:
    path = mock_dir / f"{provider}.json"
    if not path.exists():
        return None
    data = load_json(path, [])
    return data if isinstance(data, list) else None


def fetch_all(providers: list[str], runner: Runner = run_process, env: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    env = dict(env or os.environ)
    mock_dir = Path(env["CODEXBAR_HELPER_MOCK_DIR"]) if env.get("CODEXBAR_HELPER_MOCK_DIR") else None
    entries: list[dict[str, Any]] = []
    stagger = float(env.get("CODEXBAR_STAGGER", "0.5"))
    for index, provider in enumerate(providers):
        if index and stagger > 0 and not mock_dir:
            time.sleep(stagger)
        mocked = read_mock_provider(provider, mock_dir) if mock_dir else None
        if mocked is not None:
            entries.extend(mocked)
        else:
            account = state_value(key=f"account:{provider}") or None
            entries.extend(fetch_provider(provider, runner=runner, env=env, account=account))
    return entries


def successful_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(entry, stale=False) for entry in entries if not entry.get("error") and not entry.get("skipped")]


def merge_with_cache(entries: list[dict[str, Any]], requested: list[str], last_good_path: Path) -> list[dict[str, Any]]:
    fresh = successful_entries(entries)
    previous = load_json(last_good_path, [])
    previous_ok = {entry.get("provider"): entry for entry in previous if isinstance(entry, dict) and entry.get("provider") and not entry.get("error")}

    if fresh:
        merged_cache = dict(previous_ok)
        for entry in fresh:
            clean = dict(entry)
            clean.pop("stale", None)
            merged_cache[clean.get("provider")] = clean
        write_json(last_good_path, list(merged_cache.values()))
        previous_ok = merged_cache

    seen = {entry.get("provider") for entry in entries if entry.get("provider")}
    output: list[dict[str, Any]] = []
    for entry in entries:
        provider = entry.get("provider")
        if entry.get("error") and provider in previous_ok:
            output.append(dict(previous_ok[provider], stale=True))
        else:
            output.append(entry)
    for provider in requested:
        if provider not in seen and provider in previous_ok:
            output.append(dict(previous_ok[provider], stale=True))
    return output


def provider_name(provider_id: str | None) -> str:
    if not provider_id:
        return "Provider"
    return PROVIDER_NAMES.get(provider_id, provider_id.replace("-", " ").replace("_", " ").title())


def token_accounts(provider_config: dict[str, Any] | None) -> list[dict[str, str]]:
    if not provider_config:
        return []
    token_data = provider_config.get("tokenAccounts")
    raw_accounts = token_data.get("accounts", []) if isinstance(token_data, dict) else []
    active_index = token_data.get("activeIndex", 0) if isinstance(token_data, dict) else 0
    accounts: list[dict[str, str]] = []
    for index, account in enumerate(raw_accounts):
        if not isinstance(account, dict):
            continue
        label = str(account.get("label") or account.get("id") or f"Account {index + 1}")
        accounts.append({"label": label, "id": str(account.get("id") or ""), "active": str(index == active_index).lower()})
    return accounts


def identity_text(entry: dict[str, Any], provider_config: dict[str, Any] | None = None, include_email: bool = True) -> str:
    usage_obj = entry.get("usage")
    usage = usage_obj if isinstance(usage_obj, dict) else {}
    identity_obj = usage.get("identity")
    identity = identity_obj if isinstance(identity_obj, dict) else {}
    parts = []
    if include_email:
        email = usage.get("accountEmail") or identity.get("accountEmail") or identity.get("email")
        if email:
            parts.append(str(email))
    org = usage.get("accountOrganization") or identity.get("accountOrganization") or identity.get("organization")
    login = usage.get("loginMethod") or identity.get("loginMethod")
    if org:
        parts.append(str(org))
    if login:
        parts.append(str(login))
    if parts:
        return " · ".join(parts)

    accounts = token_accounts(provider_config)
    active = next((account for account in accounts if account.get("active") == "true"), None)
    if active:
        return active["label"]
    if accounts:
        return accounts[0]["label"]
    return ""


def window_percent(entry: dict[str, Any], key: str) -> float | None:
    usage_obj = entry.get("usage")
    usage = usage_obj if isinstance(usage_obj, dict) else {}
    window_obj = usage.get(key)
    window = window_obj if isinstance(window_obj, dict) else None
    value = window.get("usedPercent") if window else None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def max_percent(entry: dict[str, Any]) -> float:
    values = [window_percent(entry, key) for key in WINDOW_LABELS]
    return max([value for value in values if value is not None], default=0.0)


def pct_label(value: float) -> str:
    return f"{int(value)}%" if value.is_integer() else f"{value:.1f}%"


def reset_text(window: dict[str, Any] | None) -> str:
    if not isinstance(window, dict):
        return ""
    desc = str(window.get("resetDescription") or "").strip()
    if desc:
        return desc
    iso = window.get("resetsAt")
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone()
    except ValueError:
        return ""
    return dt.strftime("%b %-d at %-I:%M %p %Z")


def tooltip_lines(entries: list[dict[str, Any]], configs: dict[str, dict[str, Any]] | None = None) -> list[str]:
    lines: list[str] = []
    configs = configs or {}
    for entry in entries:
        name = provider_name(entry.get("provider"))
        account = identity_text(entry, configs.get(str(entry.get("provider"))))
        if account:
            name = f"{name} ({account})"
        if entry.get("error"):
            message = entry.get("error", {}).get("message", "unknown error")
            lines.append(f"{name}: error — {message}")
            continue
        usage_obj = entry.get("usage")
        usage = usage_obj if isinstance(usage_obj, dict) else {}
        for key, label in WINDOW_LABELS.items():
            window_obj = usage.get(key)
            window = window_obj if isinstance(window_obj, dict) else None
            percent = window_percent(entry, key)
            if percent is None:
                continue
            suffix = reset_text(window)
            stale = " (stale)" if entry.get("stale") else ""
            lines.append(f"{name} {label.lower()}: {pct_label(percent)}" + (f" — {suffix}" if suffix else "") + stale)
    return lines


def bar_text(entries: list[dict[str, Any]], pinned_provider: str = "") -> str:
    pinned = next((entry for entry in entries if pinned_provider and entry.get("provider") == pinned_provider), None)
    if pinned and not pinned.get("error"):
        values = [window_percent(pinned, "primary"), window_percent(pinned, "secondary")]
        values = [value for value in values if value is not None]
        if len(values) >= 2:
            return f"{pct_label(values[0])} • {pct_label(values[1])}"
        if values:
            return pct_label(values[0])
    usable = [max_percent(entry) for entry in entries if not entry.get("error")]
    if usable:
        return pct_label(max(usable))
    return "⚠"


def classify(entries: list[dict[str, Any]]) -> str:
    if not entries or all(entry.get("error") for entry in entries):
        return "stale"
    pct = max([max_percent(entry) for entry in entries if not entry.get("error")], default=0.0)
    if pct >= 90:
        return "critical"
    if pct >= 70:
        return "warning"
    if any(entry.get("stale") for entry in entries):
        return "stale"
    return "ok"


def enrich_entries(entries: list[dict[str, Any]], configs: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    enriched = []
    configs = configs or {}
    for entry in entries:
        item = dict(entry)
        provider_id = str(item.get("provider") or "")
        config = configs.get(provider_id)
        item["displayName"] = provider_name(provider_id)
        item["accountText"] = identity_text(item, config)
        item["accountPlan"] = identity_text(item, config, include_email=False)
        item["accounts"] = token_accounts(config)
        item["maxPercent"] = max_percent(item)
        enriched.append(item)
    return enriched


def summarize(entries: list[dict[str, Any]], pinned_provider: str = "", configs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    configs = configs or {}
    entries = [entry for entry in entries if not entry.get("skipped")]
    pct = max([max_percent(entry) for entry in entries if not entry.get("error")], default=0.0)
    lines = tooltip_lines(entries, configs)
    providers = enrich_entries(entries, configs)
    return {
        "text": bar_text(providers, pinned_provider),
        "tooltip": "\n".join(lines) if lines else "CodexBar: no provider data",
        "class": classify(providers),
        "percentage": pct,
        "barProvider": pinned_provider,
        "providers": _sort_by_order(providers),
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def connect_hint(provider_id: str) -> str:
    hints = {
        "codex": "Run `codex login`, then refresh CodexBar KDE.",
        "claude": "Run `claude /login`, then refresh CodexBar KDE. The helper uses OAuth and falls back to the Claude CLI source.",
        "gemini": "Run `gcloud auth application-default login`, then refresh CodexBar KDE.",
        "openrouter": "Set an API key in CodexBar config, then enable this provider.",
        "deepseek": "Set an API key in CodexBar config, then enable this provider.",
        "opencode": "OpenCode currently uses CodexBar web support, which is macOS-only in the current CLI.",
        "opencodego": "OpenCode Go currently uses CodexBar web/local support, which is macOS-only in the current CLI.",
    }
    return hints.get(provider_id, "Enable the provider, configure its credentials in CodexBar, then refresh.")


def settings_payload(config_path: Path | None = None, state_path: Path | None = None) -> dict[str, Any]:
    config_path = config_path or paths().config
    configs = provider_config_map(config_path)
    sf = state_full(state_path)
    ids = sorted(set(PROVIDER_NAMES) | set(configs))
    providers = []
    for provider_id in ids:
        config = configs.get(provider_id, {})
        linux_unsupported = sys.platform.startswith("linux") and provider_id in LINUX_UNSUPPORTED_WEB_PROVIDERS
        providers.append({
            "id": provider_id,
            "displayName": provider_name(provider_id),
            "enabled": bool(config.get("enabled")),
            "source": str(config.get("source") or config.get("cookieSource") or "auto"),
            "userSource": sf.get(f"source:{provider_id}", ""),
            "availableSources": source_options(provider_id),
            "userAccount": sf.get(f"account:{provider_id}", ""),
            "linuxSupported": not linux_unsupported,
            "linuxUnsupportedMessage": connect_hint(provider_id) if linux_unsupported else "",
            "accountText": identity_text({"provider": provider_id}, config),
            "accounts": token_accounts(config),
            "connectHint": connect_hint(provider_id),
        })
    pinnable = [
        {"id": str(item["id"]), "displayName": provider_name(str(item["id"]))}
        for item in providers
        if item["enabled"] and item["linuxSupported"]
    ]
    return {
        "providers": providers,
        "pinnableProviders": pinnable,
        "pinnedProvider": sf.get("barProvider", ""),
        "refreshIntervalSeconds": int(sf.get("refreshIntervalSeconds", "30") or "30"),
        "allAccounts": sf.get("allAccounts", "true") != "false",
        "statusPages": sf.get("statusPages", "false") == "true",
        "noCredits": sf.get("noCredits", "false") == "true",
        "showBarText": sf.get("showBarText", "true") != "false",
        "providerOrder": sf.get("providerOrder", "[]"),
        "showAccountEmail": sf.get("showAccountEmail", "true") != "false",
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def command_settings(args: argparse.Namespace) -> int:
    json.dump(settings_payload(), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def command_state(args: argparse.Namespace) -> int:
    json.dump(state_full(), sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def command_set_state(args: argparse.Namespace) -> int:
    sf = state_full()
    if args.key:
        sf[args.key] = args.value
    _write_state(sf)
    return 0


def command_batch_set_state(args: argparse.Namespace) -> int:
    sf = state_full()
    for key, value in json.loads(args.json):
        sf[key] = value
    _write_state(sf)
    return 0


def command_set_provider(args: argparse.Namespace) -> int:
    enabled = args.enabled if isinstance(args.enabled, bool) else str(args.enabled).lower() == "true"
    action = "enable" if enabled else "disable"
    proc = run_process([codexbar_binary(os.environ), "config", action, "--provider", args.provider], dict(os.environ))
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout or f"codexbar config {action} failed").strip(), file=sys.stderr)
        return proc.returncode or 1
    return command_settings(args)


def command_summary(args: argparse.Namespace) -> int:
    p = paths()
    providers = enabled_providers(p.config)
    raw = fetch_all(providers)
    merged = merge_with_cache(raw, providers, p.last_good)
    payload = summarize(merged, state_value(p.state), provider_config_map(p.config))
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def command_cache(args: argparse.Namespace) -> int:
    cached = load_json(paths().last_good, [])
    payload = summarize(cached if isinstance(cached, list) else [], state_value(paths().state), provider_config_map(paths().config))
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def command_providers(args: argparse.Namespace) -> int:
    json.dump(enabled_providers(paths().config), sys.stdout)
    sys.stdout.write("\n")
    return 0


def _run_codexbar(sub: list[str]) -> subprocess.CompletedProcess[str]:
    return run_process([codexbar_binary(os.environ)] + sub, dict(os.environ))


def command_cost(args: argparse.Namespace) -> int:
    proc = _run_codexbar(["cost", "--format", "json", "--no-color"])
    if proc.returncode != 0 and not proc.stdout.strip():
        print((proc.stderr or "codexbar cost failed").strip(), file=sys.stderr)
        return proc.returncode or 1
    data = json.loads(proc.stdout or "[]")
    payload = {
        "cost": data if isinstance(data, list) else [],
        "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def command_cache_clear(args: argparse.Namespace) -> int:
    proc = _run_codexbar(["cache", "clear", "--all"])
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout or "cache clear failed").strip(), file=sys.stderr)
        return proc.returncode or 1
    p = paths()
    write_json(p.last_good, [])
    print("{}", file=sys.stdout)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CodexBar KDE data helper")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary", help="Fetch providers and print the Plasma summary JSON").set_defaults(func=command_summary)
    sub.add_parser("cache", help="Print a summary from the last-good cache only").set_defaults(func=command_cache)
    sub.add_parser("providers", help="Print enabled provider IDs").set_defaults(func=command_providers)
    sub.add_parser("settings", help="Print provider settings for the Plasma settings view").set_defaults(func=command_settings)
    sub.add_parser("state", help="Print the current state.json contents").set_defaults(func=command_state)
    sub.add_parser("cost", help="Print cost/credit data from codexbar cost").set_defaults(func=command_cost)
    sub.add_parser("cache-clear", help="Clear CodexBar caches and the widget last-good cache").set_defaults(func=command_cache_clear)
    set_state = sub.add_parser("set-state", help="Update a key in the widget state file")
    set_state.add_argument("--key", required=True, help="State key (e.g. account:codex)")
    set_state.add_argument("--value", required=True, help="State value")
    set_state.set_defaults(func=command_set_state)
    batch = sub.add_parser("batch-set-state", help="Apply multiple state changes at once")
    batch.add_argument("--json", required=True, help="JSON array of [key,value] pairs")
    batch.set_defaults(func=command_batch_set_state)
    set_provider = sub.add_parser("set-provider", help="Enable or disable a provider through codexbar config")
    set_provider.add_argument("--provider", required=True)
    set_provider.add_argument("--enabled", choices=["true", "false"], required=True)
    set_provider.set_defaults(func=command_set_provider)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
