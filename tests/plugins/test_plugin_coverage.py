"""Tests for plugin coverage gaps.

Covers missed lines in:
- agent_skills/discovery.py
"""

from unittest.mock import patch

# ─── agent_skills/discovery.py ─────────────────────────────────────────


class TestDiscoveryMissedLines:
    """Tests for discovery.py lines 72-79 (None directories branch) and 95 (warning)."""

    def test_discover_skills_none_directories_uses_config(self, tmp_path):
        """Lines 72-79: when directories=None, merges config + defaults."""
        from fid_coder.plugins.agent_skills.discovery import discover_skills

        skill_dir = tmp_path / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Skill")

        with (
            patch(
                "fid_coder.plugins.agent_skills.discovery.get_skill_directories",
                return_value=[str(tmp_path / "skills")],
            ),
            patch(
                "fid_coder.plugins.agent_skills.discovery.get_default_skill_directories",
                return_value=[tmp_path / "skills"],  # same as config, tests dedup
            ),
        ):
            results = discover_skills(directories=None)
            assert any(s.name == "my-skill" for s in results)

    def test_discover_skills_path_not_directory(self, tmp_path):
        """Line 95: warning when skill path is not a directory."""
        # Create a file where a directory is expected
        not_a_dir = tmp_path / "not-a-dir"
        not_a_dir.write_text("I'm a file")

        from fid_coder.plugins.agent_skills.discovery import discover_skills

        results = discover_skills(directories=[not_a_dir])
        assert results == []
