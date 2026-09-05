import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ate_opportunity_scanner import core


class MetadataPrivacyTests(unittest.TestCase):
    def test_mcp_config_uses_keys_not_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".mcp.json"
            path.write_text(json.dumps({
                "mcpServers": {
                    "postgres": {
                        "command": "npx",
                        "env": {"API_TOKEN": "supersecretvalue"},
                        "args": ["postgres://user:password@example.invalid/database"],
                    }
                }
            }))
            terms = core.metadata_terms(path)
            self.assertIn("postgres", terms)
            self.assertIn("api", terms)
            self.assertNotIn("supersecretvalue", terms)
            self.assertNotIn("password", terms)
            self.assertNotIn("example.invalid", terms)

    def test_package_manifest_keeps_dependency_names_not_script_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.json"
            path.write_text(json.dumps({
                "name": "accessible-dashboard",
                "dependencies": {"react": "latest", "playwright": "latest"},
                "scripts": {"test:e2e": "secret-command --token hiddenvalue"},
            }))
            terms = core.metadata_terms(path)
            self.assertIn("react", terms)
            self.assertIn("playwright", terms)
            self.assertIn("test", terms)
            self.assertNotIn("secret-command", terms)
            self.assertNotIn("hiddenvalue", terms)

    def test_sensitive_files_and_symlinks_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("SECRET=do-not-read")
            (root / "package.json").write_text('{"dependencies":{"react":"1"}}')
            (root / "linked.json").symlink_to(root / "package.json")
            context = core.collect_context(root)
            self.assertIn("react", context.terms)
            self.assertNotIn("secret", context.terms)
            self.assertGreaterEqual(context.files_skipped, 2)

    def test_filesystem_root_is_rejected(self):
        with self.assertRaises(ValueError):
            core.collect_context(Path(Path.cwd().anchor))

    def test_agent_configuration_detection_is_opt_in(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            core, "detect_agents", return_value=["Codex"]
        ), mock.patch.object(core, "detected_server_names", return_value={"existing"}):
            default_context = core.collect_context(Path(directory))
            opted_in_context = core.collect_context(Path(directory), include_agent_configs=True)
            self.assertEqual(default_context.detected_agents, [])
            self.assertEqual(default_context.installed_servers, set())
            self.assertEqual(opted_in_context.detected_agents, ["Codex"])
            self.assertEqual(opted_in_context.installed_servers, {"existing"})

    def test_configured_server_names_ignore_server_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(
                '[mcp_servers.database]\ncommand = "secret-command"\n'
                '[mcp_servers.database.env]\nAPI_TOKEN = "hiddenvalue"\n'
            )
            self.assertEqual(core.configured_server_names(path), {"database"})


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.context = core.ProjectContext(root=Path("/tmp/dashboard"))
        self.context.terms.update(core.tokenize("react typescript playwright accessibility frontend browser testing"))
        core.expand_capabilities(self.context.terms)
        self.rows = [
            {
                "mcp_id": "a" * 16,
                "tool_name": "scan_accessibility",
                "server_name": "browser-a11y",
                "tool_description": "Run browser accessibility tests for React pages with Playwright",
                "task_text": "Test web applications",
                "occupation_title": "Web Developers",
            },
            {
                "mcp_id": "b" * 16,
                "tool_name": "cancel_order",
                "server_name": "commerce",
                "tool_description": "Cancel and refund a customer order",
                "task_text": "Cancel orders",
                "occupation_title": "Online Merchants",
            },
        ]

    def test_relevant_tool_ranks_first(self):
        candidates = core.rank_candidates(self.context, self.rows, limit=2)
        self.assertEqual(candidates[0].row["tool_name"], "scan_accessibility")

    def test_destructive_tool_is_high_risk(self):
        level, signals = core.classify_risk("Delete an order and issue a refund")
        self.assertEqual(level, "high")
        self.assertIn("delete", signals)

    def test_report_does_not_include_absolute_project_path(self):
        candidate = core.rank_candidates(self.context, self.rows, limit=1)[0]
        report = core.render_report(self.context, [candidate])
        self.assertNotIn("/tmp/dashboard", report)
        self.assertIn("MCP opportunities for dashboard", report)
        self.assertIn("An MCP tool is a callable function", report)
        self.assertIn("until you delete it", report)
        self.assertIn("Agent configuration check: not requested", report)
        self.assertIn("Considered", report)

    def test_report_distinguishes_checked_agent_configuration(self):
        self.context.agent_configs_checked = True
        self.context.detected_agents = []
        report = core.render_report(self.context, [])
        self.assertIn("no recognized agent folders found", report)

    def test_report_shortens_descriptions_at_a_word_boundary(self):
        candidate = core.Candidate(
            score=1,
            row={"tool_name": "long", "server_name": "example", "tool_description": "word " * 120},
            signals=[],
            risk_level="low",
            risk_signals=[],
        )
        report = core.render_report(self.context, [candidate])
        description_line = next(line for line in report.splitlines() if "Published description:" in line)
        self.assertTrue(description_line.endswith("word…"))

    def test_report_escapes_untrusted_markdown(self):
        candidate = core.Candidate(
            score=1,
            row={
                "tool_name": "[click](https://attacker.invalid)",
                "server_name": "<script>alert(1)</script>",
                "tool_description": "![track](https://attacker.invalid/pixel)",
            },
            signals=["browser"],
            risk_level="low",
            risk_signals=[],
        )
        report = core.render_report(self.context, [candidate])
        self.assertNotIn("![track]", report)
        self.assertNotIn("<script>", report)
        self.assertIn("\\[click\\]", report)

    def test_existing_server_is_not_recommended(self):
        self.context.installed_servers.add("browser-a11y")
        candidates = core.rank_candidates(self.context, self.rows, limit=2)
        self.assertTrue(all(candidate.row["server_name"] != "browser-a11y" for candidate in candidates))

    def test_report_signals_do_not_disclose_private_project_terms(self):
        context = core.ProjectContext(root=Path("/tmp/privatecodename"))
        context.terms.update(core.tokenize("privatecodename react browser testing"))
        candidate = core.rank_candidates(context, [{
            "mcp_id": "c" * 16,
            "tool_name": "privatecodename_browser_test",
            "server_name": "testing",
            "tool_description": "Test privatecodename React applications in a browser",
            "task_text": "Browser testing for applications",
            "occupation_title": "Web Developers",
        }], limit=1)[0]
        report = core.render_report(context, [candidate])
        self.assertNotIn("Matching signals: privatecodename", report)


class CatalogTests(unittest.TestCase):
    def test_catalog_download_writes_only_returned_rows(self):
        responses = [
            {"num_rows_total": 2, "rows": [{"row": {"tool_name": "one"}}]},
            {"num_rows_total": 2, "rows": [{"row": {"tool_name": "two"}}]},
        ]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            core, "_request_json", side_effect=responses
        ), mock.patch.object(core.shutil, "which", return_value=None):
            destination = Path(directory) / "catalog.jsonl"
            core.download_catalog(destination)
            rows = list(core.iter_catalog(destination))
            self.assertEqual([row["tool_name"] for row in rows], ["one", "two"])

    def test_dataset_download_rejects_untrusted_host(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                core._download_file(
                    "https://attacker.invalid/catalog.parquet",
                    Path(directory) / "catalog.parquet",
                    100,
                )

    def test_catalog_does_not_execute_duckdb_from_working_directory(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            core.shutil, "which", return_value=str(Path(directory) / "duckdb")
        ), mock.patch.object(core, "_download_catalog_via_api") as fallback, mock.patch.object(
            core.Path, "cwd", return_value=Path(directory)
        ):
            destination = Path(directory) / "catalog.jsonl"
            core.download_catalog(destination)
            fallback.assert_called_once_with(destination)

    def test_offline_enrichment_rejects_untrusted_repository_url(self):
        candidate = core.Candidate(
            score=1,
            row={"github_url": "https://attacker.invalid/repository"},
            signals=[],
            risk_level="low",
            risk_signals=[],
        )
        core.enrich_candidates([candidate], offline=True)
        self.assertIsNone(candidate.repository)


if __name__ == "__main__":
    unittest.main()
