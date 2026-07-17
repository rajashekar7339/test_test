"""Version reporting utilities for Fid Coder."""

from fid_coder.messaging import emit_info, emit_warning, get_message_bus
from fid_coder.messaging.messages import VersionCheckMessage


def default_version_mismatch_behavior(current_version):
    # Defensive: ensure current_version is never None
    if current_version is None:
        current_version = "0.0.0-unknown"
        emit_warning("Could not detect current version, using fallback")

    # This fork isn't published to PyPI, so there is no upstream version to
    # compare against. Report the current version only.
    version_msg = VersionCheckMessage(
        current_version=current_version,
        latest_version=current_version,
        update_available=False,
    )
    get_message_bus().emit(version_msg)

    emit_info(f"Current version: {current_version}")
