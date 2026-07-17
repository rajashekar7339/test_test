from unittest.mock import patch

from fid_coder.version_checker import default_version_mismatch_behavior


class TestDefaultVersionMismatchBehavior:
    """Test default_version_mismatch_behavior function.

    This fork isn't published to PyPI, so the function no longer fetches an
    upstream version to compare against -- it only reports the current
    version.
    """

    @patch("fid_coder.version_checker.get_message_bus")
    @patch("fid_coder.version_checker.emit_warning")
    @patch("fid_coder.version_checker.emit_info")
    def test_shows_current_version_only(
        self, mock_emit_info, mock_emit_warning, mock_bus
    ):
        """Test that only the current version is reported, with no update check."""
        default_version_mismatch_behavior("1.0.0")

        mock_emit_info.assert_called_once_with("Current version: 1.0.0")
        mock_emit_warning.assert_not_called()

    @patch("fid_coder.version_checker.get_message_bus")
    @patch("fid_coder.version_checker.emit_warning")
    @patch("fid_coder.version_checker.emit_info")
    def test_none_current_version_handled_gracefully(
        self, mock_emit_info, mock_emit_warning, mock_bus
    ):
        """Test that None current_version is handled gracefully."""
        # This should not raise an exception
        default_version_mismatch_behavior(None)

        # Should emit warning about unknown version
        mock_emit_warning.assert_called_once_with(
            "Could not detect current version, using fallback"
        )
        # Should use fallback version in info message
        mock_emit_info.assert_called_once_with("Current version: 0.0.0-unknown")
