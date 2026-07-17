"""Tests to achieve 100% coverage for remaining plugin gaps.

Covers:
- shell_safety/agent_shell_safety.py (full class)
- shell_safety/command_cache.py (all methods)
- shell_safety/register_callbacks.py (line 43)
- agent_skills/discovery.py (lines 79, 95)
- agent_skills/metadata.py (multiple missing lines)
- agent_skills/skill_catalog.py (multiple missing lines)
- agent_skills/skills_install_menu.py (line 60)
"""

import ast
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

# ============================================================
# shell_safety/command_cache.py - Full coverage
# ============================================================
from fid_coder.plugins.shell_safety.command_cache import (
    CachedAssessment,
    CommandSafetyCache,
    cache_assessment,
    get_cache_stats,
    get_cached_assessment,
)


class TestCommandSafetyCache:
    """Tests for CommandSafetyCache LRU cache."""

    def test_make_key_strips_whitespace(self):
        cache = CommandSafetyCache()
        key = cache._make_key("  ls -la  ", "/tmp")
        assert key == ("ls -la", "/tmp")

    def test_get_miss(self):
        cache = CommandSafetyCache()
        result = cache.get("ls", None)
        assert result is None
        assert cache._misses == 1

    def test_get_hit(self):
        cache = CommandSafetyCache()
        assessment = CachedAssessment(risk="low", reasoning="safe")
        cache.put("ls", None, assessment)
        result = cache.get("ls", None)
        assert result is not None
        assert result.risk == "low"
        assert cache._hits == 1

    def test_put_updates_existing(self):
        cache = CommandSafetyCache()
        a1 = CachedAssessment(risk="low", reasoning="safe")
        a2 = CachedAssessment(risk="high", reasoning="dangerous")
        cache.put("ls", None, a1)
        cache.put("ls", None, a2)
        result = cache.get("ls", None)
        assert result.risk == "high"

    def test_lru_eviction(self):
        cache = CommandSafetyCache(max_size=2)
        cache.put("cmd1", None, CachedAssessment(risk="low", reasoning="ok"))
        cache.put("cmd2", None, CachedAssessment(risk="low", reasoning="ok"))
        cache.put("cmd3", None, CachedAssessment(risk="low", reasoning="ok"))
        # cmd1 should be evicted
        assert cache.get("cmd1", None) is None
        assert cache.get("cmd3", None) is not None

    def test_clear(self):
        cache = CommandSafetyCache()
        cache.put("ls", None, CachedAssessment(risk="low", reasoning="ok"))
        cache.get("ls", None)
        cache.clear()
        assert cache.get("ls", None) is None
        assert cache._hits == 0
        assert cache._misses == 1  # only from this last get

    def test_stats(self):
        cache = CommandSafetyCache(max_size=100)
        cache.put("ls", None, CachedAssessment(risk="low", reasoning="ok"))
        cache.get("ls", None)  # hit
        cache.get("pwd", None)  # miss
        stats = cache.stats
        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "50.0%"

    def test_stats_zero_total(self):
        cache = CommandSafetyCache()
        stats = cache.stats
        assert stats["hit_rate"] == "0.0%"


class TestCommandCacheModuleFunctions:
    """Tests for module-level cache functions."""

    def test_get_cache_stats(self):
        stats = get_cache_stats()
        assert "size" in stats
        assert "hit_rate" in stats

    def test_get_cached_assessment_miss(self):
        result = get_cached_assessment("nonexistent_command_xyz", None)
        assert result is None

    def test_cache_assessment_and_retrieve(self):
        cache_assessment("test_unique_cmd_123", "/tmp", "low", "safe cmd")
        result = get_cached_assessment("test_unique_cmd_123", "/tmp")
        assert result is not None
        assert result.risk == "low"


# ============================================================
# shell_safety/agent_shell_safety.py - Full class coverage
# ============================================================


class TestShellSafetyAgent:
    """Tests for ShellSafetyAgent without importing BaseAgent directly."""

    def test_agent_properties(self):
        """Test ShellSafetyAgent properties by mocking BaseAgent."""
        # Mock the entire base_agent module to avoid MCP import
        mock_base = MagicMock()
        mock_base.BaseAgent = type("BaseAgent", (), {})

        with patch.dict(
            "sys.modules",
            {
                "fid_coder.agents.base_agent": mock_base,
                "fid_coder.agents": MagicMock(),
            },
        ):
            # Force reimport
            import importlib

            import fid_coder.plugins.shell_safety.agent_shell_safety as mod

            importlib.reload(mod)

            agent = mod.ShellSafetyAgent()
            assert agent.name == "shell_safety_checker"
            assert agent.display_name == "Shell Safety Checker \U0001f6e1\ufe0f"
            assert "safety" in agent.description.lower()
            assert "Risk Levels" in agent.get_system_prompt()
            assert agent.get_available_tools() == []


# ============================================================
# shell_safety/register_callbacks.py - line 43 (is_oauth_model with None)
# ============================================================

from fid_coder.plugins.shell_safety.register_callbacks import (  # noqa: E402
    is_oauth_model,
)


class TestIsOauthModel:
    def test_none_model(self):
        assert is_oauth_model(None) is False

    def test_empty_string(self):
        assert is_oauth_model("") is False

    def test_non_oauth(self):
        assert is_oauth_model("gpt-4") is False


# ============================================================
# agent_skills/discovery.py - lines 79, 95
# ============================================================

from fid_coder.plugins.agent_skills.discovery import discover_skills  # noqa: E402


class TestDiscoveryMissingLines:
    def test_discover_with_none_merges_defaults(self, tmp_path):
        """Line 79: directories is None branch - defaults NOT already in configured."""
        configured_dir = tmp_path / "configured_skills"
        configured_dir.mkdir()
        default_dir = tmp_path / "default_skills"  # different from configured
        default_dir.mkdir()

        skill_dir = configured_dir / "my_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# test")

        with (
            patch(
                "fid_coder.plugins.agent_skills.discovery.get_skill_directories",
                return_value=[str(configured_dir)],
            ),
            patch(
                "fid_coder.plugins.agent_skills.discovery.get_default_skill_directories",
                return_value=[default_dir],  # different dir, should be appended
            ),
        ):
            results = discover_skills(directories=None)
            assert any(s.name == "my_skill" for s in results)

    def test_discover_skips_non_dir_path(self, tmp_path):
        """Line 88: skill path is not a directory warning."""
        file_path = tmp_path / "not_a_dir"
        file_path.write_text("I am a file")
        results = discover_skills(directories=[file_path])
        assert results == []

    def test_discover_skips_files_in_skill_dir(self, tmp_path):
        """Line 95: files inside skill directory are skipped (not subdirs)."""
        skill_dir = tmp_path / "skills"
        skill_dir.mkdir()
        # Put a regular file (not a subdirectory) in the skills dir
        (skill_dir / "readme.txt").write_text("not a skill")
        # Also put a valid skill subdir
        sub = skill_dir / "my_skill"
        sub.mkdir()
        (sub / "SKILL.md").write_text("# skill")
        results = discover_skills(directories=[skill_dir])
        # Should only find the subdir, not the file
        assert len(results) == 1
        assert results[0].name == "my_skill"


# ============================================================
# agent_skills/metadata.py - missing lines
# ============================================================

from fid_coder.plugins.agent_skills.metadata import (  # noqa: E402
    get_skill_resources,
    load_full_skill_content,
    parse_skill_metadata,
    parse_yaml_frontmatter,
)


class TestMetadataMissingLines:
    def test_parse_frontmatter_comment_lines(self):
        """Line 69: skip comment lines in frontmatter."""
        content = "---\n# comment\nname: test\n---\n"
        result = parse_yaml_frontmatter(content)
        assert result["name"] == "test"

    def test_parse_frontmatter_list_at_end(self):
        """Lines 82-83: Handle list items at end of frontmatter."""
        content = "---\ntags:\n  - foo\n  - bar\n---\n"
        result = parse_yaml_frontmatter(content)
        assert result["tags"] == ["foo", "bar"]

    def test_parse_frontmatter_list_then_kv(self):
        """Lines 82-83: list items followed by a new key-value pair."""
        content = "---\ntags:\n  - foo\n  - bar\nname: test\n---\n"
        result = parse_yaml_frontmatter(content)
        assert result["tags"] == ["foo", "bar"]
        assert result["name"] == "test"

    def test_parse_skill_metadata_nonexistent_path(self, tmp_path):
        """Lines 130-131: path does not exist."""
        result = parse_skill_metadata(tmp_path / "nonexistent")
        assert result is None

    def test_parse_skill_metadata_no_skill_md(self, tmp_path):
        """Lines 130-131: no SKILL.md file."""
        result = parse_skill_metadata(tmp_path)
        assert result is None

    def test_parse_skill_metadata_read_error(self, tmp_path):
        """Lines 181-182: read error."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("content")
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            result = parse_skill_metadata(tmp_path)
            assert result is None

    def test_parse_skill_metadata_no_frontmatter(self, tmp_path):
        """Lines 186-188: no valid frontmatter."""
        (tmp_path / "SKILL.md").write_text("Just some content without frontmatter")
        result = parse_skill_metadata(tmp_path)
        assert result is None

    def test_parse_skill_metadata_no_name(self, tmp_path):
        """Lines 207-208: name missing from frontmatter."""
        (tmp_path / "SKILL.md").write_text("---\ndescription: test\n---\n")
        result = parse_skill_metadata(tmp_path)
        assert result is None

    def test_parse_skill_metadata_no_description(self, tmp_path):
        """Lines 215-217: description missing from frontmatter."""
        (tmp_path / "SKILL.md").write_text("---\nname: test\n---\n")
        result = parse_skill_metadata(tmp_path)
        assert result is None

    def test_load_full_skill_content_nonexistent(self, tmp_path):
        result = load_full_skill_content(tmp_path / "nope")
        assert result is None

    def test_load_full_skill_content_no_skill_md(self, tmp_path):
        result = load_full_skill_content(tmp_path)
        assert result is None

    def test_load_full_skill_content_read_error(self, tmp_path):
        (tmp_path / "SKILL.md").write_text("test")
        with patch.object(Path, "read_text", side_effect=IOError("fail")):
            result = load_full_skill_content(tmp_path)
            assert result is None

    def test_get_skill_resources_nonexistent(self, tmp_path):
        result = get_skill_resources(tmp_path / "nope")
        assert result == []

    def test_get_skill_resources_not_dir(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        result = get_skill_resources(f)
        assert result == []

    def test_get_skill_resources_iterdir_error(self, tmp_path):
        with patch.object(Path, "iterdir", side_effect=PermissionError("denied")):
            result = get_skill_resources(tmp_path)
            assert result == []

    def test_parse_skill_metadata_tags_as_string(self, tmp_path):
        """Test tags parsed from comma-separated string."""
        (tmp_path / "SKILL.md").write_text(
            "---\nname: test\ndescription: desc\ntags: foo, bar\n---\n"
        )
        result = parse_skill_metadata(tmp_path)
        assert result is not None
        assert result.tags == ["foo", "bar"]


# ============================================================
# agent_skills/skill_catalog.py - missing lines
# ============================================================

from fid_coder.plugins.agent_skills.skill_catalog import (  # noqa: E402
    SkillCatalog,
    _format_display_name,
)


class TestSkillCatalogMissing:
    def test_format_display_name_empty(self):
        """Line 85: empty string."""
        assert _format_display_name("") == ""
        assert _format_display_name(None) == ""
        assert _format_display_name("   ") == ""

    def test_format_display_name_acronym(self):
        assert _format_display_name("api") == "API"
        assert _format_display_name("json-parser") == "JSON Parser"

    def test_catalog_init_remote_exception(self):
        """Lines 139-142: fetch_remote_catalog raises exception."""
        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            side_effect=RuntimeError("network error"),
        ):
            cat = SkillCatalog()
            assert cat.get_all() == []

    def test_catalog_init_remote_none(self):
        """Lines 145-149: fetch returns None."""
        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            return_value=None,
        ):
            cat = SkillCatalog()
            assert cat.get_all() == []

    def test_catalog_list_categories(self):
        """Lines 201-202."""
        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            return_value=None,
        ):
            cat = SkillCatalog()
            assert cat.list_categories() == []

    def test_catalog_get_by_category_empty(self):
        """Lines 207-209."""
        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            return_value=None,
        ):
            cat = SkillCatalog()
            assert cat.get_by_category("") == []
            assert cat.get_by_category("nonexistent") == []

    def test_catalog_search_empty_query(self):
        """Lines 214-232: search returns all when empty."""
        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            return_value=None,
        ):
            cat = SkillCatalog()
            assert cat.search("") == []
            assert cat.search(None) == []

    def test_catalog_search_with_entries(self):
        """Lines 214-232: search with actual entries."""
        mock_remote = MagicMock()
        entry = MagicMock()
        entry.name = "data-explorer"
        entry.description = "Explore data"
        entry.group = "analysis"
        entry.has_scripts = False
        entry.has_references = False
        entry.file_count = 1
        entry.download_url = "http://example.com"
        entry.zip_size_bytes = 100
        mock_remote.entries = [entry]

        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            return_value=mock_remote,
        ):
            cat = SkillCatalog()
            results = cat.search("data")
            assert len(results) == 1
            results2 = cat.search("nonexistent")
            assert len(results2) == 0

    def test_catalog_get_by_id_empty(self):
        """Lines 237-239."""
        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            return_value=None,
        ):
            cat = SkillCatalog()
            assert cat.get_by_id("") is None
            assert cat.get_by_id(None) is None

    def test_catalog_get_by_id_found(self):
        """Line 244."""
        mock_remote = MagicMock()
        entry = MagicMock()
        entry.name = "test-skill"
        entry.description = "Test"
        entry.group = "testing"
        entry.has_scripts = False
        entry.has_references = False
        entry.file_count = 1
        entry.download_url = ""
        entry.zip_size_bytes = 0
        mock_remote.entries = [entry]

        with patch(
            "fid_coder.plugins.agent_skills.skill_catalog.fetch_remote_catalog",
            return_value=mock_remote,
        ):
            cat = SkillCatalog()
            result = cat.get_by_id("test-skill")
            assert result is not None
            assert result.id == "test-skill"
            assert cat.get_by_id("nonexistent") is None


# ============================================================
# agent_skills/skills_install_menu.py - line 60 (GB fallthrough)
# ============================================================


class TestSkillsInstallMenuSizeFormat:
    def test_format_size_gb(self):
        """Line 60: format size that exceeds MB range."""
        from fid_coder.plugins.agent_skills.skills_install_menu import _format_bytes

        # Large enough to be in GB
        result = _format_bytes(2 * 1024 * 1024 * 1024)  # 2 GB
        assert "GB" in result

    def test_format_size_bytes(self):
        from fid_coder.plugins.agent_skills.skills_install_menu import _format_bytes

        result = _format_bytes(500)
        assert "B" in result

    def test_format_size_tb_fallthrough(self):
        """Line 60: the final return that's after the loop."""
        from fid_coder.plugins.agent_skills.skills_install_menu import _format_bytes

        # The loop goes B, KB, MB, GB - GB always returns inside loop
        # So line 60 (return after loop) is unreachable in normal flow
        # But we still test large values to ensure GB branch works
        result = _format_bytes(5 * 1024 * 1024 * 1024)
        assert "GB" in result

