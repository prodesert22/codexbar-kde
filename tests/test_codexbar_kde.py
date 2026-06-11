from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HELPER_PATH = Path(__file__).resolve().parents[1] / "package" / "contents" / "code" / "codexbar_kde.py"
spec = importlib.util.spec_from_file_location("codexbar_kde", HELPER_PATH)
assert spec and spec.loader
helper = importlib.util.module_from_spec(spec)
sys.modules["codexbar_kde"] = helper
spec.loader.exec_module(helper)


def provider_entry(provider: str, primary: int, secondary: int = 0, tertiary: int = 0):
    return {
        "provider": provider,
        "usage": {
            "primary": {"usedPercent": primary, "resetDescription": "Resets in 1 hour"},
            "secondary": {"usedPercent": secondary, "resetDescription": "Resets Monday"},
            "tertiary": {"usedPercent": tertiary},
        },
    }


class CodexBarKdeTests(unittest.TestCase):
    def setUp(self):
        self._state = {}
        self._orig_state_value = helper.state_value
        self._orig_state_full = helper.state_full

        def _mock_state_value(state_path=None, key="barProvider", default=""):
            if state_path is not None:
                return self._orig_state_value(state_path, key, default)
            val = self._state.get(key, default)
            return str(val) if val is not None else default

        def _mock_state_full(state_path=None):
            if state_path is not None:
                return self._orig_state_full(state_path)
            return dict(self._state)

        setattr(helper, "state_value", _mock_state_value)
        setattr(helper, "state_full", _mock_state_full)

    def tearDown(self):
        setattr(helper, "state_value", self._orig_state_value)
        setattr(helper, "state_full", self._orig_state_full)

    def test_enabled_providers_from_env_or_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "providers": [
                            {"id": "codex", "enabled": True},
                            {"id": "claude", "enabled": False},
                            {"id": "gemini", "enabled": True},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(helper.enabled_providers(config, env={}), ["codex", "gemini"])
            self.assertEqual(
                helper.enabled_providers(config, env={"CODEXBAR_PROVIDERS": "claude openrouter"}),
                ["claude", "openrouter"],
            )

    def test_summary_pinned_provider_and_warning_class(self):
        entries = [provider_entry("codex", 4, 12), provider_entry("claude", 75, 20)]
        payload = helper.summarize(entries, pinned_provider="codex")

        self.assertEqual(payload["text"], "4% • 12%")
        self.assertEqual(payload["class"], "warning")
        self.assertEqual(payload["percentage"], 75)
        self.assertIn("Claude session: 75%", payload["tooltip"])

    def test_cache_replaces_provider_error_with_stale_last_good(self):
        with tempfile.TemporaryDirectory() as tmp:
            last_good = Path(tmp) / "last.json"
            helper.write_json(last_good, [provider_entry("codex", 7, 14)])

            merged = helper.merge_with_cache(
                [{"provider": "codex", "error": {"message": "HTTP 429"}}],
                ["codex"],
                last_good,
            )

            self.assertEqual(len(merged), 1)
            self.assertTrue(merged[0]["stale"])
            self.assertEqual(merged[0]["usage"]["primary"]["usedPercent"], 7)

    def test_claude_oauth_error_falls_back_to_cli(self):
        calls = []

        def runner(args, env):
            calls.append(args)
            if args[-1] == "oauth":
                stdout = json.dumps([{"provider": "claude", "error": {"message": "rate limited"}}])
            else:
                stdout = json.dumps([provider_entry("claude", 3, 9)])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

        entries = helper.fetch_provider("claude", runner=runner, env={"CODEXBAR_BIN": "codexbar"})

        self.assertEqual(entries[0]["usage"]["secondary"]["usedPercent"], 9)
        self.assertEqual(calls[0][-1], "oauth")
        self.assertEqual(calls[1][-1], "cli")

    def test_fetch_once_requests_all_accounts_by_default(self):
        calls = []

        def runner(args, env):
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        helper.fetch_once("codex", "oauth", runner=runner, env={"CODEXBAR_BIN": "codexbar"})

        self.assertIn("--all-accounts", calls[0])

    def test_set_provider_accepts_enabled_string(self):
        calls = []

        def runner(args, env):
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        old = helper.run_process
        old_settings = helper.command_settings
        try:
            setattr(helper, "run_process", runner)
            setattr(helper, "command_settings", lambda args: 0)
            code = helper.command_set_provider(type("Args", (), {"provider": "opencode", "enabled": "false"})())
        finally:
            setattr(helper, "run_process", old)
            setattr(helper, "command_settings", old_settings)

        self.assertEqual(code, 0)
        self.assertEqual(calls[0][1:4], ["config", "disable", "--provider"])

    def test_codexbar_binary_prefers_path_before_local_default(self):
        path = helper.codexbar_binary(env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(path, "/usr/bin/codexbar")

    def test_missing_codexbar_binary_returns_provider_error(self):
        entries = helper.fetch_once("codex", "oauth", env={"CODEXBAR_BIN": "/definitely/missing/codexbar"})

        self.assertEqual(entries[0]["provider"], "codex")
        self.assertIn("CodexBar CLI not found", entries[0]["error"]["message"])

    def test_linux_unsupported_web_provider_is_not_fetched(self):
        def runner(args, env):
            raise AssertionError("unsupported provider should not call codexbar")

        entries = helper.fetch_provider("opencodego", runner=runner, env={"CODEXBAR_BIN": "codexbar"})

        self.assertTrue(entries[0]["linuxUnsupported"])
        self.assertTrue(entries[0]["skipped"])
        self.assertIn("Linux", entries[0]["warning"]["message"])

    def test_summary_hides_skipped_linux_unsupported_providers(self):
        payload = helper.summarize([
            provider_entry("codex", 10),
            {"provider": "opencodego", "skipped": True, "linuxUnsupported": True},
        ])

        self.assertEqual(len(payload["providers"]), 1)
        self.assertEqual(payload["providers"][0]["provider"], "codex")

    def test_identity_email_is_added_to_enriched_provider(self):
        entries = [{
            "provider": "codex",
            "usage": {
                "identity": {"accountEmail": "new@example.com", "loginMethod": "oauth"},
                "primary": {"usedPercent": 5},
            },
        }]

        payload = helper.summarize(entries)

        self.assertEqual(payload["providers"][0]["accountText"], "new@example.com · oauth")
        self.assertEqual(payload["providers"][0]["accountPlan"], "oauth")
        self.assertIn("Codex (new@example.com · oauth) session: 5%", payload["tooltip"])

    def test_identity_extracts_email_from_top_level_usage(self):
        """Claude may return accountEmail at usage level, not nested under identity."""
        entries = [{
            "provider": "claude",
            "usage": {
                "accountEmail": "dev@anthropic.com",
                "accountOrganization": "MyOrg",
                "primary": {"usedPercent": 50},
            },
        }]

        payload = helper.summarize(entries)

        self.assertEqual(payload["providers"][0]["accountText"], "dev@anthropic.com · MyOrg")
        self.assertEqual(payload["providers"][0]["accountPlan"], "MyOrg")
        self.assertIn("Claude (dev@anthropic.com · MyOrg)", payload["tooltip"])

    def test_settings_payload_defaults_show_account_email_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps({"providers": []}), encoding="utf-8")

            payload = helper.settings_payload(config_path, state_path=Path(tmp) / "state.json")
            self.assertTrue(payload["showAccountEmail"], "showAccountEmail should default to true")

    def test_settings_payload_lists_token_accounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.json"
            config.write_text(
                json.dumps({
                    "providers": [{
                        "id": "opencodego",
                        "enabled": True,
                        "tokenAccounts": {
                            "activeIndex": 1,
                            "accounts": [
                                {"id": "a", "label": "old@example.com"},
                                {"id": "b", "label": "new@example.com"},
                            ],
                        },
                    }]
                }),
                encoding="utf-8",
            )

            payload = helper.settings_payload(config)
            opencodego = next(item for item in payload["providers"] if item["id"] == "opencodego")

            self.assertEqual(opencodego["accountText"], "new@example.com")
            self.assertFalse(opencodego["linuxSupported"])
            self.assertEqual(len(opencodego["accounts"]), 2)

    def test_source_options_returns_known_sources_for_codex(self):
        sources = helper.source_options("codex")
        self.assertIn("oauth", sources)
        self.assertIn("cli", sources)
        self.assertIn("auto", sources)

    def test_source_options_falls_back_to_default_for_unknown(self):
        sources = helper.source_options("nonexistent_provider_xyz")
        self.assertIn("auto", sources)

    def test_fetch_once_respects_state_all_accounts_off(self):
        calls = []
        self._state["allAccounts"] = "false"

        def runner(args, env):
            calls.append(list(args))
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        helper.fetch_once("codex", "oauth", runner=runner, env={"CODEXBAR_BIN": "codexbar", "CODEXBAR_ALL_ACCOUNTS": "1"})

        self.assertNotIn("--all-accounts", calls[0])

    def test_fetch_once_passes_explicit_account_flag(self):
        calls = []

        def runner(args, env):
            calls.append(list(args))
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        helper.fetch_once("codex", "oauth", runner=runner, env={"CODEXBAR_BIN": "codexbar", "CODEXBAR_ALL_ACCOUNTS": "0"}, account="pedro@example.com")

        self.assertIn("--account", calls[0])
        idx = calls[0].index("--account")
        self.assertEqual(calls[0][idx + 1], "pedro@example.com")
        self.assertNotIn("--all-accounts", calls[0])

    def test_settings_payload_includes_global_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps({"providers": []}), encoding="utf-8")
            helper.write_json(state_path, {"refreshIntervalSeconds": "45", "allAccounts": "false", "account:codex": "user@example.com", "source:codex": "cli"})

            payload = helper.settings_payload(config_path, state_path)
            self.assertEqual(payload["refreshIntervalSeconds"], 45)
            self.assertEqual(payload["allAccounts"], False)

            codex = next(item for item in payload["providers"] if item["id"] == "codex")
            self.assertEqual(codex["userAccount"], "user@example.com")
            self.assertEqual(codex["userSource"], "cli")
            self.assertIn("oauth", codex["availableSources"])

    def test_fetch_once_includes_status_flag_when_enabled(self):
        calls = []
        self._state["statusPages"] = "true"

        def runner(args, env):
            calls.append(list(args))
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        helper.fetch_once("codex", "oauth", runner=runner, env={"CODEXBAR_BIN": "codexbar", "CODEXBAR_ALL_ACCOUNTS": "0"}, account="test@example.com")

        self.assertIn("--status", calls[0])

    def test_fetch_once_omits_status_flag_by_default(self):
        calls = []

        def runner(args, env):
            calls.append(list(args))
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        helper.fetch_once("codex", "oauth", runner=runner, env={"CODEXBAR_BIN": "codexbar", "CODEXBAR_ALL_ACCOUNTS": "0"}, account="test@example.com")

        self.assertNotIn("--status", calls[0])

    def test_command_cost_runs_codexbar_cost(self):
        def runner(args, env):
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='[{"provider":"codex","last30DaysCostUSD":1.23}]', stderr="")

        old = helper.run_process
        try:
            setattr(helper, "run_process", runner)
            code = helper.command_cost(type("Args", (), {})())
        finally:
            setattr(helper, "run_process", old)

        self.assertEqual(code, 0)

    def test_command_cache_clear_runs_and_resets_last_good(self):
        calls = []

        def runner(args, env):
            calls.append(args[-1])
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

        old = helper.run_process
        try:
            setattr(helper, "run_process", runner)
            code = helper.command_cache_clear(type("Args", (), {})())
        finally:
            setattr(helper, "run_process", old)

        self.assertEqual(code, 0)
        self.assertEqual(calls[0], "--all")

    def test_settings_payload_includes_pinned_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            config_path = Path(tmp) / "config.json"
            config_path.write_text(json.dumps({
                "providers": [
                    {"id": "codex", "enabled": True},
                    {"id": "claude", "enabled": True},
                    {"id": "opencode", "enabled": False},
                ]
            }), encoding="utf-8")
            helper.write_json(state_path, {"barProvider": "codex"})

            payload = helper.settings_payload(config_path, state_path)
            self.assertEqual(payload["pinnedProvider"], "codex")
            self.assertEqual(len(payload["pinnableProviders"]), 2)
            self.assertEqual(payload["pinnableProviders"][0]["id"], "claude")
            self.assertEqual(payload["pinnableProviders"][1]["id"], "codex")

    def test_no_credits_flag_is_passed_when_enabled(self):
        calls = []
        self._state["noCredits"] = "true"

        def runner(args, env):
            calls.append(list(args))
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        helper.fetch_once("codex", "oauth", runner=runner, env={"CODEXBAR_BIN": "codexbar", "CODEXBAR_ALL_ACCOUNTS": "0"}, account="test@example.com")

        self.assertIn("--no-credits", calls[0])

    def test_no_credits_flag_omitted_by_default(self):
        calls = []

        def runner(args, env):
            calls.append(list(args))
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]", stderr="")

        helper.fetch_once("codex", "oauth", runner=runner, env={"CODEXBAR_BIN": "codexbar", "CODEXBAR_ALL_ACCOUNTS": "0"}, account="test@example.com")

        self.assertNotIn("--no-credits", calls[0])

    def test_provider_order_sorts_providers(self):
        entries = [
            provider_entry("claude", 10),
            provider_entry("codex", 20),
            provider_entry("gemini", 30),
        ]
        self._state["providerOrder"] = json.dumps(["gemini", "codex"])

        payload = helper.summarize(entries)
        ids = [p["provider"] for p in payload["providers"]]
        self.assertEqual(ids, ["gemini", "codex", "claude"])

    def test_provider_order_ignored_when_empty(self):
        entries = [
            provider_entry("codex", 10),
            provider_entry("claude", 5),
        ]

        payload = helper.summarize(entries)
        ids = [p["provider"] for p in payload["providers"]]
        self.assertEqual(ids, ["codex", "claude"])


if __name__ == "__main__":
    unittest.main()
