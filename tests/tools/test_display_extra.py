"""Extra tests for display.py line 39 (subagent skip)."""

from unittest.mock import patch


class TestDisplaySubagentSkip:
    @patch("fid_coder.tools.display.get_subagent_verbose", return_value=False)
    @patch("fid_coder.tools.display.is_subagent", return_value=True)
    def test_skips_for_subagent(self, mock_sub, mock_verbose):
        from fid_coder.tools.display import display_non_streamed_result

        # Should return early without doing anything
        result = display_non_streamed_result("test content")
        assert result is None
