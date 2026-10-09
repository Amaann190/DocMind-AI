import unittest

from utils.llama_index import EXCLUDED_FILE_PATTERNS


class DualModeChatTests(unittest.TestCase):
    def test_excluded_file_patterns_contain_common_binaries(self):
        self.assertIn("*.png", EXCLUDED_FILE_PATTERNS)
        self.assertIn("*.exe", EXCLUDED_FILE_PATTERNS)
        self.assertIn("*.zip", EXCLUDED_FILE_PATTERNS)
        self.assertIn("*.pyc", EXCLUDED_FILE_PATTERNS)
        self.assertIn("*.mp4", EXCLUDED_FILE_PATTERNS)


if __name__ == "__main__":
    unittest.main()
