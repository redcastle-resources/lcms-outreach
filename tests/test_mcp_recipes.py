import io
import unittest
from contextlib import redirect_stdout

from lcms_outreach.mcp.datasets import LCMS_DATASET, TCC_DATASET, format_datasets
from lcms_outreach.mcp.prompts import RECIPES, format_recipes
from lcms_outreach.mcp.server import main


class DatasetTests(unittest.TestCase):
    def test_dataset_ids_are_exposed(self):
        self.assertEqual(LCMS_DATASET.asset_id, "USFS/GTAC/LCMS/v2024-10")
        self.assertEqual(TCC_DATASET.asset_id, "USGS/NLCD_RELEASES/2016_REL")

    def test_dataset_summary_includes_bands(self):
        summary = format_datasets()
        self.assertIn("Land_Cover", summary)
        self.assertIn("percent_tree_cover", summary)


class RecipeTests(unittest.TestCase):
    def test_recipes_include_expected_topics(self):
        self.assertGreaterEqual(len(RECIPES), 4)
        formatted = format_recipes()
        self.assertIn("land-cover-change", formatted)
        self.assertIn("integrated-report", formatted)

    def test_help_mode_prints_wrapper_help(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--help"])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("lcms-outreach MCP wrapper", output)
        self.assertIn("USFS/GTAC/LCMS/v2024-10", output)

    def test_recipes_mode_prints_prompt_text(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--recipes"])
        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Prompt recipes:", output)
        self.assertIn("percent_tree_cover", output)


if __name__ == "__main__":
    unittest.main()
