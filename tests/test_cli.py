import tempfile
import unittest
from pathlib import Path

from ate_opportunity_scanner.cli import main


class CliTests(unittest.TestCase):
    def test_offline_scan_writes_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "web-dashboard"
            project.mkdir()
            (project / "package.json").write_text(
                '{"dependencies":{"react":"1","playwright":"1"}}'
            )
            catalog = root / "catalog.jsonl"
            catalog.write_text(
                '{"mcp_id":"aaaaaaaaaaaaaaaa","tool_name":"scan_accessibility",'
                '"server_name":"a11y","tool_description":"browser accessibility testing for react and playwright",'
                '"task_text":"Test web applications","occupation_title":"Web Developers"}\n'
            )
            output = root / "result.md"
            result = main([
                str(project), "--catalog", str(catalog), "--offline", "--output", str(output)
            ])
            self.assertEqual(result, 0)
            self.assertIn("scan\\_accessibility", output.read_text())


if __name__ == "__main__":
    unittest.main()
