"""P0 module-graph gate contracts (no fixtures, no I/O outside tmp_path)."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_module_graph.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_module_graph", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_module_graph"] = module
    spec.loader.exec_module(module)
    return module


cmg = _load()


def _scan(files: dict[str, str], packages: set[str] | None = None):
    modules = {mod: Path(f"{mod.replace('.', '/')}.py") for mod in files}
    trees = {mod: ast.parse(src) for mod, src in files.items()}
    return modules, trees, packages if packages is not None else set()


def test_resolve_import_absolute_is_exact():
    # Regression: absolute `from X import y` must resolve to X itself, not
    # to the importer's package with X appended.
    _, _, packages = _scan({"paperforge.actions.registry": ""})
    absolute = ast.parse("from paperforge.lineage import x\n").body[0]
    assert cmg.resolve_import("paperforge.actions.registry", absolute, packages) == [
        ("paperforge.lineage", "x")
    ]
    heavy = ast.parse("from PIL import Image\n").body[0]
    assert cmg.resolve_import("paperforge.worker.ocr", heavy, packages) == [
        ("PIL", "Image")
    ]
    sibling = ast.parse("from . import helper\n").body[0]
    assert cmg.resolve_import("paperforge.p.main", sibling, packages) == [
        ("paperforge.p", "helper")
    ]
    up_one = ast.parse("from .. import sib\n").body[0]
    assert cmg.resolve_import("paperforge.p.sub.main", up_one, {"paperforge.p"}) == [
        ("paperforge.p", "sib")
    ]


def test_ring_detected():
    graph = {"a": {"b"}, "b": {"a"}, "c": set()}
    assert cmg.find_rings(graph) == [["a", "b"]]


def test_dag_has_no_rings():
    assert cmg.find_rings({"a": {"b"}, "b": {"c"}, "c": set()}) == []


def test_self_import_is_a_ring():
    assert cmg.find_rings({"a": {"a"}}) == [["a"]]


def test_graph_sees_guarded_imports_but_not_function_ones():
    modules, trees, packages = _scan(
        {
            "paperforge.a": (
                "try:\n"
                "    import paperforge.b\n"
                "except ImportError:\n"
                "    pass\n"
                "if True:\n"
                "    from paperforge import c\n"
                "def f():\n"
                "    import paperforge.hidden\n"
            ),
            "paperforge.b": "",
            "paperforge": "",
        }
    )
    graph = cmg.collect_graph(modules, trees, packages)
    assert graph["paperforge.a"] == {"paperforge.b", "paperforge"}


def test_graph_skips_type_checking_blocks():
    modules, trees, packages = _scan(
        {
            "paperforge.a": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    import paperforge.b\n"
            ),
            "paperforge.b": "",
        }
    )
    assert cmg.collect_graph(modules, trees, packages)["paperforge.a"] == set()


def test_from_package_import_resolves_child_submodule():
    modules, trees, packages = _scan(
        {
            "paperforge": "",
            "paperforge.commands": "",
            "paperforge.worker.status": "from paperforge import commands\n",
        }
    )
    graph = cmg.collect_graph(modules, trees, packages)
    assert graph["paperforge.worker.status"] == {"paperforge.commands"}


def test_relative_child_import_resolves():
    modules, trees, packages = _scan(
        {
            "paperforge.p": "",
            "paperforge.p.helper": "",
            "paperforge.p.main": "from . import helper\n",
        }
    )
    graph = cmg.collect_graph(modules, trees, packages)
    assert graph["paperforge.p.main"] == {"paperforge.p.helper"}


def test_self_name_import_is_a_self_edge():
    # `from P import M` inside P/M.py binds the partially initialized
    # sys.modules entry for M itself: a real self-edge, not just the parent.
    modules, trees, packages = _scan(
        {
            "paperforge": "",
            "paperforge.p": "",
            "paperforge.p.m": "from paperforge.p import m\n",
        }
    )
    graph = cmg.collect_graph(modules, trees, packages)
    assert graph["paperforge.p.m"] == {"paperforge.p.m"}
    assert cmg.find_rings(graph) == [["paperforge.p.m"]]


def test_true_self_import_is_a_ring():
    modules, trees, packages = _scan(
        {"paperforge": "", "paperforge.a": "import paperforge.a\n"}
    )
    graph = cmg.collect_graph(modules, trees, packages)
    assert "paperforge.a" in graph["paperforge.a"]
    assert cmg.find_rings(graph) == [["paperforge.a"]]


def test_explicit_package_init_cycle_detected():
    modules, trees, packages = _scan(
        {
            "paperforge": "",
            "paperforge.a": "from paperforge.a import b\n",
            "paperforge.a.b": "import paperforge.a\n",
        },
        packages={"paperforge", "paperforge.a"},
    )
    graph = cmg.collect_graph(modules, trees, packages)
    assert graph["paperforge.a"] == {"paperforge.a.b"}
    assert graph["paperforge.a.b"] == {"paperforge.a"}
    assert cmg.find_rings(graph) == [["paperforge.a", "paperforge.a.b"]]


def test_r2_cross_package_private_name_frozen():
    modules, trees, packages = _scan(
        {"paperforge.actions.registry": "from paperforge.lineage import _detect_residuals\n"}
    )
    private, layer, heavy = cmg.collect_violations(modules, trees, packages)
    assert private == {"paperforge.actions.registry": ["1:paperforge.lineage:_detect_residuals"]}
    assert layer == {}
    assert heavy == {}


def test_r2_private_module_segment_frozen():
    modules, trees, packages = _scan(
        {"paperforge.commands.ocr": "from paperforge.worker._utils import pipeline_paths\n"}
    )
    private, _, _ = cmg.collect_violations(modules, trees, packages)
    assert private == {"paperforge.commands.ocr": ["1:paperforge.worker._utils"]}


def test_r2_same_package_private_use_allowed():
    modules, trees, packages = _scan(
        {"paperforge.worker.ocr": "from paperforge.worker._utils import pipeline_paths\n"}
    )
    assert cmg.collect_violations(modules, trees, packages) == ({}, {}, {})


def test_r2_dunder_and_local_alias_allowed():
    modules, trees, packages = _scan(
        {
            "paperforge.commands.action": (
                "from paperforge import __version__\n"
                "from paperforge.lineage import scope_from_dict as _s\n"
            )
        }
    )
    assert cmg.collect_violations(modules, trees, packages) == ({}, {}, {})


def _member_accesses(files: dict[str, str]):
    modules, trees, packages = _scan(files)
    return cmg.collect_private_member_accesses(modules, trees, packages)


def _entry(line: int, target: str, member: str):
    return {"line": line, "target_module": target, "member": member}


def test_r2b_import_as_alias_member_access_flagged():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "import paperforge.worker.asset_index as asset_index\n"
                "x = asset_index._compute_export_hash({})\n"
            ),
        }
    )
    assert found == {
        "paperforge.probes.library": [
            _entry(2, "paperforge.worker.asset_index", "_compute_export_hash")
        ]
    }


def test_r2b_plain_import_dotted_member_access_flagged():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "import paperforge.worker.asset_index\n"
                "x = paperforge.worker.asset_index._compute_export_hash({})\n"
            ),
        }
    )
    assert found == {
        "paperforge.probes.library": [
            _entry(2, "paperforge.worker.asset_index", "_compute_export_hash")
        ]
    }


def test_r2b_from_import_alias_member_access_flagged():
    # Probe-style function-level import.
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "def f(paths):\n"
                "    from paperforge.worker import asset_index as asset_index\n"
                "    return asset_index._compute_export_hash(paths)\n"
            ),
        }
    )
    assert found == {
        "paperforge.probes.library": [
            _entry(3, "paperforge.worker.asset_index", "_compute_export_hash")
        ]
    }


def test_r2b_same_package_sibling_member_access_flagged():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.worker.ocr": (
                "import paperforge.worker.asset_index as asset_index\n"
                "x = asset_index._compute_export_hash({})\n"
            ),
        }
    )
    assert found == {
        "paperforge.worker.ocr": [
            _entry(2, "paperforge.worker.asset_index", "_compute_export_hash")
        ]
    }


def test_r2b_module_alias_visible_in_function_unless_shadowed():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "import paperforge.worker.asset_index as asset_index\n"
                "def f(paths):\n"
                "    return asset_index._compute_export_hash(paths)\n"
            ),
        }
    )
    assert found == {
        "paperforge.probes.library": [
            _entry(3, "paperforge.worker.asset_index", "_compute_export_hash")
        ]
    }


def test_r2b_function_local_alias_does_not_leak():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "def f(paths):\n"
                "    from paperforge.worker import asset_index\n"
                "    return asset_index._compute_export_hash(paths)\n"
                "def g(paths):\n"
                "    return asset_index._compute_export_hash(paths)\n"
            ),
        }
    )
    assert found == {
        "paperforge.probes.library": [
            _entry(3, "paperforge.worker.asset_index", "_compute_export_hash")
        ]
    }


def test_r2b_parameter_shadowing_suppresses_flag():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "import paperforge.worker.asset_index as asset_index\n"
                "def f(asset_index):\n"
                "    return asset_index._compute_export_hash({})\n"
            ),
        }
    )
    assert found == {}


def test_r2b_nested_private_base_is_not_a_module():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "import paperforge.worker.asset_index as asset_index\n"
                "x = asset_index._cache._key\n"
            ),
        }
    )
    assert found == {
        "paperforge.probes.library": [_entry(2, "paperforge.worker.asset_index", "_cache")]
    }


def test_r2b_same_module_private_use_allowed():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": (
                "import paperforge.worker.asset_index as asset_index\n"
                "x = asset_index._compute_export_hash({})\n"
            ),
        }
    )
    assert found == {}


def test_r2b_public_and_dunder_member_use_allowed():
    found = _member_accesses(
        {
            "paperforge.worker.asset_index": "",
            "paperforge.probes.library": (
                "import paperforge.worker.asset_index as asset_index\n"
                "a = asset_index.read_index(None)\n"
                "b = asset_index.__version__\n"
            ),
        }
    )
    assert found == {}


def test_r2b_non_module_alias_ignored():
    found = _member_accesses(
        {
            "paperforge.actions.registry": (
                "from paperforge.lineage import scope_from_dict as _s\n"
                "x = _s._private\n"
            ),
        }
    )
    assert found == {}


def test_r2b_exception_matched_by_target_not_line():
    snapshot = {
        "rings": [],
        "private_imports": {},
        "layer_violations": {},
        "heavy_imports": {},
        "private_member_accesses": {
            "paperforge.probes.library": [
                _entry(114, "paperforge.worker.asset_index", "_compute_export_hash")
            ]
        },
    }
    ratchet = {
        "rings": [],
        "private_imports": {},
        "layer_violations": {},
        "heavy_imports": {},
        "private_member_access_exceptions": {
            "paperforge.probes.library": ["paperforge.worker.asset_index:_compute_export_hash"]
        },
    }
    assert cmg.check(snapshot, ratchet) == []
    other = dict(
        snapshot,
        private_member_accesses={
            "paperforge.probes.library": [
                _entry(114, "paperforge.worker.asset_index", "_other_helper")
            ]
        },
    )
    failures = cmg.check(other, ratchet)
    assert len(failures) == 1 and "R2b" in failures[0]


def test_r3_worker_to_commands_blocked_at_any_level():
    modules, trees, packages = _scan(
        {
            "paperforge.worker.status": (
                "def f():\n"
                "    from paperforge.commands.ocr import _collect_ocr_health_summary\n"
            )
        }
    )
    _, layer, _ = cmg.collect_violations(modules, trees, packages)
    assert layer == {
        "paperforge.worker.status": ["2:paperforge.commands.ocr:_collect_ocr_health_summary"]
    }


def test_r3_from_package_root_import_blocked():
    modules, trees, packages = _scan(
        {
            "paperforge": "",
            "paperforge.commands": "",
            "paperforge.worker.status": "from paperforge import commands\n",
        }
    )
    _, layer, _ = cmg.collect_violations(modules, trees, packages)
    assert layer == {"paperforge.worker.status": ["1:paperforge.commands:commands"]}


def test_r3_commands_to_worker_allowed():
    modules, trees, packages = _scan(
        {"paperforge.commands.ocr": "from paperforge.worker.ocr import run_ocr\n"}
    )
    assert cmg.collect_violations(modules, trees, packages) == ({}, {}, {})


def test_r4_top_level_heavy_blocked_but_lazy_allowed():
    modules, trees, packages = _scan(
        {
            "paperforge.worker.ocr": (
                "from PIL import Image\n" "def f():\n" "    import torch\n"
            )
        }
    )
    _, _, heavy = cmg.collect_violations(modules, trees, packages)
    assert heavy == {"paperforge.worker.ocr": ["1:PIL"]}


def test_r4_guarded_heavy_blocked_but_type_checking_allowed():
    modules, trees, packages = _scan(
        {
            "paperforge.a": (
                "try:\n"
                "    import chromadb\n"
                "except ImportError:\n"
                "    pass\n"
            ),
            "paperforge.b": (
                "from typing import TYPE_CHECKING\n"
                "if TYPE_CHECKING:\n"
                "    import torch\n"
            ),
        }
    )
    _, _, heavy = cmg.collect_violations(modules, trees, packages)
    assert heavy == {"paperforge.a": ["2:chromadb"]}


def test_r4_class_body_import_is_eager_but_method_lazy():
    # A class suite executes at module import; only method bodies defer.
    modules, trees, packages = _scan(
        {
            "paperforge.a": (
                "class C:\n"
                "    import torch\n"
                "    def m(self):\n"
                "        import fitz\n"
            )
        }
    )
    _, _, heavy = cmg.collect_violations(modules, trees, packages)
    assert heavy == {"paperforge.a": ["2:torch"]}


def test_check_passes_clean_and_shrink_is_allowed():
    snapshot = {"rings": [], "private_imports": {}, "layer_violations": {}, "heavy_imports": {}}
    bloated = {
        "rings": [],
        "private_imports": {"paperforge.a": ["1:paperforge.b:_old"]},
        "layer_violations": {},
        "heavy_imports": {},
    }
    assert cmg.check(snapshot, snapshot) == []
    assert cmg.check(snapshot, bloated) == []  # fixed entries just go stale


def test_repository_module_graph_ratchet_passes():
    assert cmg.main(["--check"]) == 0


def test_check_red_on_new_violation():
    ratchet = {"rings": [], "private_imports": {}, "layer_violations": {}, "heavy_imports": {}}
    snapshot = {
        "rings": [],
        "private_imports": {"paperforge.a": ["3:paperforge.b:_new"]},
        "layer_violations": {},
        "heavy_imports": {},
    }
    failures = cmg.check(snapshot, ratchet)
    assert len(failures) == 1 and "R2" in failures[0]


def test_r1_strict_below_threshold_but_no_new_rings_above():
    frozen = [f"ring:paperforge.m{i:02d},paperforge.n{i:02d}" for i in range(10)]
    ratchet = {
        "r1_no_new_rings": True,
        "rings": frozen,
        "private_imports": {},
        "layer_violations": {},
        "heavy_imports": {},
    }
    same = dict(ratchet)
    assert cmg.check(same, ratchet) == []
    grown = dict(ratchet, rings=frozen + ["ring:paperforge.x,paperforge.y"])
    failures = cmg.check(grown, ratchet)
    assert len(failures) == 1 and "R1" in failures[0]


def test_r1_any_ring_fails_when_not_downgraded():
    ratchet = {"rings": [], "private_imports": {}, "layer_violations": {}, "heavy_imports": {}}
    snapshot = dict(ratchet, rings=["ring:paperforge.a,paperforge.b"])
    failures = cmg.check(snapshot, ratchet)
    assert len(failures) == 1 and "R1" in failures[0]


def test_resolve_callee_redirects_into_child_submodule():
    known = {"fake_pkg", "fake_pkg.child"}
    seen = {}
    has_func = lambda mod, qual: seen.setdefault((mod, qual), (mod, qual) == ("fake_pkg.child", "worker"))
    assert cmg._resolve_callee("fake_pkg", "child", "worker", known, has_func) == "fake_pkg.child:worker"
    assert cmg._resolve_callee("fake_pkg", "child", None, known, has_func) is None
    assert cmg._resolve_callee("fake_pkg", "missing", "worker", known, has_func) is None


def test_reach_closure_isolated(tmp_path, monkeypatch):
    entry_p = tmp_path / "fake_entry.py"
    entry_p.write_text(
        "from fake_lib import helper\n"
        "def entry():\n"
        "    helper()\n"
        "    local()\n"
        "    leaked()\n"
        "    def nested():\n"
        "        nested_only()\n"
        "def local():\n"
        "    return 1\n"
        "def uncalled():\n"
        "    return 2\n"
        "def unrelated():\n"
        "    from fake_lib import leaked, nested_only\n"
        "    leaked()\n"
    )
    lib_p = tmp_path / "fake_lib.py"
    lib_p.write_text(
        "def helper():\n    return 3\n"
        "def leaked():\n    return 4\n"
        "def nested_only():\n    return 5\n"
    )
    monkeypatch.setattr(
        cmg, "iter_modules", lambda: {"fake_entry": entry_p, "fake_lib": lib_p}
    )
    reached, _ = cmg.reach("fake_entry:entry")
    assert reached == ["fake_entry:entry", "fake_entry:local", "fake_lib:helper"]


def test_reach_follows_called_nested_function(tmp_path, monkeypatch):
    entry_p = tmp_path / "fake_entry.py"
    entry_p.write_text(
        "from fake_lib import helper\n"
        "def entry():\n"
        "    def nested():\n"
        "        helper()\n"
        "    def unused():\n"
        "        ignored()\n"
        "    nested()\n"
    )
    lib_p = tmp_path / "fake_lib.py"
    lib_p.write_text(
        "def helper():\n    return 1\n"
        "def ignored():\n    return 2\n"
    )
    monkeypatch.setattr(
        cmg, "iter_modules", lambda: {"fake_entry": entry_p, "fake_lib": lib_p}
    )
    reached, _ = cmg.reach("fake_entry:entry")
    assert reached == [
        "fake_entry:entry",
        "fake_entry:entry.nested",
        "fake_lib:helper",
    ]


def test_reach_follows_function_local_import(tmp_path, monkeypatch):
    entry_p = tmp_path / "fake_entry.py"
    entry_p.write_text(
        "def entry():\n"
        "    from fake_lib import helper\n"
        "    helper()\n"
    )
    lib_p = tmp_path / "fake_lib.py"
    lib_p.write_text("def helper():\n    return 1\n")
    monkeypatch.setattr(
        cmg, "iter_modules", lambda: {"fake_entry": entry_p, "fake_lib": lib_p}
    )
    reached, _ = cmg.reach("fake_entry:entry")
    assert reached == ["fake_entry:entry", "fake_lib:helper"]


def test_reach_follows_package_child_import(tmp_path, monkeypatch):
    (tmp_path / "fake_pkg").mkdir()
    (tmp_path / "fake_pkg" / "__init__.py").write_text("x = 1\n")
    (tmp_path / "fake_pkg" / "child.py").write_text("def worker():\n    return 1\n")
    main_p = tmp_path / "fake_main.py"
    main_p.write_text("from fake_pkg import child\ndef entry():\n    child.worker()\n")
    monkeypatch.setattr(
        cmg,
        "iter_modules",
        lambda: {
            "fake_pkg": tmp_path / "fake_pkg" / "__init__.py",
            "fake_pkg.child": tmp_path / "fake_pkg" / "child.py",
            "fake_main": main_p,
        },
    )
    reached, _ = cmg.reach("fake_main:entry")
    assert reached == ["fake_main:entry", "fake_pkg.child:worker"]


def test_reach_entry_present_and_deterministic():
    first, _ = cmg.reach("paperforge.worker.ocr_figures:build_figure_inventory")
    second, _ = cmg.reach("paperforge.worker.ocr_figures:build_figure_inventory")
    assert first == second
    assert "paperforge.worker.ocr_figures:build_figure_inventory" in first


def test_reach_rejects_bad_entry():
    with pytest.raises(SystemExit):
        cmg.reach("paperforge.no_such_module_xyz:func")
    with pytest.raises(SystemExit):
        cmg.reach("paperforge.config:no_such_function_xyz")
