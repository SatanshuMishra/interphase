import json
import pathlib
import re
import unittest


class TestManifest(unittest.TestCase):
    def test_manifest_names_the_plugin_interphase(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        manifest_path = root / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest["name"], "interphase")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["license"], "Apache-2.0")
        description = manifest["description"]
        self.assertIsInstance(description, str)
        self.assertTrue(len(description) > 0)
        self.assertNotIn("mitosis", description.lower())


class TestMarketplace(unittest.TestCase):
    def test_marketplace_lists_interphase_from_the_root(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        marketplace_path = root / ".claude-plugin" / "marketplace.json"
        marketplace = json.loads(marketplace_path.read_text())
        self.assertEqual(marketplace["name"], "interphase")
        plugins = marketplace["plugins"]
        self.assertEqual(len(plugins), 1)
        plugin = plugins[0]
        self.assertEqual(plugin["name"], "interphase")
        self.assertEqual(plugin["source"], "./")


if __name__ == "__main__":
    unittest.main()
