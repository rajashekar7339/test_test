"""Guardrails preventing pytest from reading or writing real user config."""

import os

from fid_coder import config


def test_fid_coder_paths_use_pytest_xdg_temp_directory():
    xdg_paths = [
        os.environ["XDG_CONFIG_HOME"],
        os.environ["XDG_DATA_HOME"],
        os.environ["XDG_CACHE_HOME"],
        os.environ["XDG_STATE_HOME"],
    ]

    assert all("fid_coder_pytest_xdg_" in path for path in xdg_paths)
    # The autouse fixture further narrows CONFIG_DIR to a per-test temp path.
    assert "fid_coder_test_config_" in config.CONFIG_DIR
    assert config.DATA_DIR.startswith(os.environ["XDG_DATA_HOME"])
    assert config.CACHE_DIR.startswith(os.environ["XDG_CACHE_HOME"])
    assert config.STATE_DIR.startswith(os.environ["XDG_STATE_HOME"])
