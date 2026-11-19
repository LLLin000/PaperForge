"""Unit tests for four-dimensional version decoupling and depsLockHash."""

from __future__ import annotations

from pathlib import Path

from paperforge.core.versioning import (
    compute_deps_lock_hash,
    is_version_compatible,
    normalize_release_version,
    parse_release_tuple,
)


def test_normalize_and_order_release_versions() -> None:
    assert normalize_release_version("v2.0.0-rc.6") == "2.0.0rc6"
    assert normalize_release_version("2.1.0-beta.2") == "2.1.0b2"
    assert normalize_release_version("2.0.0rc6.post1") == "2.0.0rc6.post1"

    assert parse_release_tuple("2.0.0a1") < parse_release_tuple("2.0.0b2")
    assert parse_release_tuple("2.0.0b2") < parse_release_tuple("2.0.0-rc.6")
    assert parse_release_tuple("2.0.0rc6") < parse_release_tuple("2.0.0rc6.post1")
    assert parse_release_tuple("2.0.0rc6.post1") < parse_release_tuple("2.0.0")
    assert parse_release_tuple("2.0.0") < parse_release_tuple("2.1.0")


def test_is_version_compatible_decoupled_and_strict_modes() -> None:
    # Strict 1:1 mode when min_engine_version is omitted
    assert is_version_compatible(core_version="2.0.0rc6", expected_version="2.0.0-rc.6") == (True, "ok")
    assert is_version_compatible(core_version="2.0.0rc6", expected_version="2.1.0") == (
        False,
        "exact_version_mismatch",
    )

    # Decoupled v2.1 mode: UI patch 2.1.4 works against core 2.1.0 when minEngineVersion=2.1.0
    assert is_version_compatible(
        core_version="2.1.0",
        expected_version="2.1.4",
        min_engine_version="2.1.0",
        min_plugin_version="2.0.0rc6",
    ) == (True, "ok")

    # Core older than minEngineVersion -> fails
    assert is_version_compatible(
        core_version="2.0.0rc6",
        expected_version="2.1.4",
        min_engine_version="2.1.0",
        min_plugin_version="2.0.0rc6",
    ) == (False, "core_below_min_engine")

    # Plugin older than core's minimum supported plugin -> fails
    assert is_version_compatible(
        core_version="2.2.0",
        expected_version="1.5.0",
        min_engine_version="1.5.0",
        min_plugin_version="2.0.0rc6",
    ) == (False, "plugin_below_min_plugin")


def test_compute_deps_lock_hash_is_deterministic_and_sensitive_to_changes(tmp_path: Path) -> None:
    real_hash = compute_deps_lock_hash()
    assert len(real_hash) == 16
    assert real_hash == compute_deps_lock_hash()

    pyproject_a = tmp_path / "a.toml"
    pyproject_b = tmp_path / "b.toml"
    pyproject_c = tmp_path / "c.toml"

    pyproject_a.write_text(
        '[project]\ndependencies = ["requests>=2.31.0", "xxhash >= 3.4.0"]\n'
        '[project.optional-dependencies]\nvector = ["openai>=1.0.0"]\ntest = ["pytest>=7.4.0"]\n',
        encoding="utf-8",
    )
    pyproject_b.write_text(
        '[project]\ndependencies = ["xxhash>=3.4.0", "requests>=2.31.0"]\n'
        '[project.optional-dependencies]\nvector = ["openai >= 1.0.0"]\ntest = ["pytest>=8.0.0"]\n',
        encoding="utf-8",
    )
    pyproject_c.write_text(
        '[project]\ndependencies = ["xxhash>=3.4.0", "requests>=2.31.0", "pymupdf>=1.24.0"]\n'
        '[project.optional-dependencies]\nvector = ["openai>=1.0.0"]\n',
        encoding="utf-8",
    )

    # Order, whitespace, and test-only changes must not change depsLockHash
    assert compute_deps_lock_hash(pyproject_a) == compute_deps_lock_hash(pyproject_b)
    # Adding/updating runtime or vector dependencies flips depsLockHash
    assert compute_deps_lock_hash(pyproject_a) != compute_deps_lock_hash(pyproject_c)


def test_runtime_abi_and_installed_dep_checks_guard_fast_patch(tmp_path: Path) -> None:
    from paperforge.core.versioning import (
        installed_deps_satisfy_declarations,
        runtime_abi_tag,
    )

    tag = runtime_abi_tag()
    assert tag.startswith("py")
    assert "-" in tag

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\ndependencies = ["requests>=2.31.0,<3"]\n',
        encoding="utf-8",
    )
    sp = tmp_path / "site-packages"
    sp.mkdir()
    # Empty/mock site-packages (no dist-info) -> allowed for unit test harnesses
    assert installed_deps_satisfy_declarations(sp, pyproject_path=pyproject) is True

    # Real outdated dist-info -> rejected cleanly
    dist_info = sp / "requests-2.20.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: requests\nVersion: 2.20.0\n",
        encoding="utf-8",
    )
    assert installed_deps_satisfy_declarations(sp, pyproject_path=pyproject) is False

    # Updating dist-info to a matching version -> satisfied cleanly
    import shutil

    shutil.rmtree(dist_info)
    good_dist = sp / "requests-2.32.3.dist-info"
    good_dist.mkdir()
    (good_dist / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: requests\nVersion: 2.32.3\n",
        encoding="utf-8",
    )
    assert installed_deps_satisfy_declarations(sp, pyproject_path=pyproject) is True
