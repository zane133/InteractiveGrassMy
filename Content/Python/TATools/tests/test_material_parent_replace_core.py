# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


CORE_PATH = Path(__file__).resolve().parents[1] / "material_parent_replace_core.py"
EXTERNAL_PATH = Path(__file__).resolve().parents[1] / "material_parent_replace_external.py"
POWERSHELL_HELPER_PATH = Path(__file__).resolve().parents[1] / "RunMaterialParentReplace.ps1"


class _FakeMaterialEditingLibrary:
    calls: list[tuple] = []
    overridden_names: set[str] = set()

    @classmethod
    def reset(cls) -> None:
        cls.calls = []
        cls.overridden_names = set()

    @classmethod
    def is_material_instance_parameter_overridden(cls, instance, name) -> bool:
        cls.calls.append(("is_overridden", str(name)))
        return str(name) in cls.overridden_names

    @classmethod
    def set_material_instance_parameter_override(
        cls, instance, name, override
    ) -> bool:
        cls.calls.append(("set_override", str(name), bool(override)))
        return True

    @classmethod
    def set_material_instance_parent(cls, instance, parent) -> None:
        cls.calls.append(("set_parent", parent))

    @classmethod
    def set_material_instance_scalar_parameter_value(
        cls, instance, name, value
    ) -> bool:
        cls.calls.append(("set_scalar", str(name), value))
        return True

    @classmethod
    def set_material_instance_vector_parameter_value(
        cls, instance, name, value
    ) -> bool:
        cls.calls.append(("set_vector", str(name), value))
        return True

    @classmethod
    def set_material_instance_texture_parameter_value(
        cls, instance, name, value
    ) -> bool:
        cls.calls.append(("set_texture", str(name), value))
        return True

    @classmethod
    def set_material_instance_static_switch_parameter_value(
        cls, instance, name, value
    ) -> bool:
        cls.calls.append(("set_static_switch", str(name), value))
        return True


class _FakeEditorAssetLibrary:
    calls: list[tuple] = []

    @classmethod
    def reset(cls) -> None:
        cls.calls = []

    @classmethod
    def save_loaded_assets(cls, assets, only_if_is_dirty=True) -> bool:
        cls.calls.append((list(assets), bool(only_if_is_dirty)))
        return True


def _load_core_module():
    fake_unreal = types.ModuleType("unreal")
    fake_unreal.MaterialEditingLibrary = _FakeMaterialEditingLibrary
    fake_unreal.EditorAssetLibrary = _FakeEditorAssetLibrary
    previous_unreal = sys.modules.get("unreal")
    sys.modules["unreal"] = fake_unreal
    try:
        spec = importlib.util.spec_from_file_location(
            "material_parent_replace_core_under_test", CORE_PATH
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_unreal is None:
            sys.modules.pop("unreal", None)
        else:
            sys.modules["unreal"] = previous_unreal


def _load_external_module():
    spec = importlib.util.spec_from_file_location(
        "material_parent_replace_external_under_test", EXTERNAL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _InstanceWithoutEditorArray:
    def get_editor_property(self, property_name):
        raise RuntimeError(f"not exposed: {property_name}")


class MaterialParentReplaceCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = _load_core_module()
        cls.external = _load_external_module()

    def setUp(self) -> None:
        _FakeMaterialEditingLibrary.reset()
        _FakeEditorAssetLibrary.reset()

    def test_getter_fallback_keeps_only_explicit_overrides(self) -> None:
        _FakeMaterialEditingLibrary.overridden_names = {"Explicit"}

        values = self.core._read_kind_overrides(
            _InstanceWithoutEditorArray(),
            "scalar_parameter_values",
            lambda instance: ["Inherited", "Explicit"],
            lambda instance, name: f"value:{name}",
        )

        self.assertEqual(values, {"Explicit": "value:Explicit"})
        self.assertEqual(
            _FakeMaterialEditingLibrary.calls,
            [
                ("is_overridden", "Inherited"),
                ("is_overridden", "Explicit"),
            ],
        )

    def test_reparent_drops_incompatible_overrides_before_parent_change(self) -> None:
        new_parent = object()

        self.core._apply_instance_reparent(
            object(),
            new_parent,
            {
                "scalar": ["OldScalar"],
                "texture": ["OldTexture"],
                "static_switch": [],
            },
        )

        self.assertEqual(
            _FakeMaterialEditingLibrary.calls,
            [
                ("set_override", "OldScalar", False),
                ("set_override", "OldTexture", False),
                ("set_parent", new_parent),
            ],
        )
        self.assertFalse(
            any(call[0].startswith("set_scalar") for call in _FakeMaterialEditingLibrary.calls)
        )

    def test_external_job_contract_is_serializable_and_normalized(self) -> None:
        payload = self.external.build_job_payload(
            "  /Old/M  ",
            " /New/M ",
            " /Game/Test ",
            1,
            auto_save=True,
        )

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["tool_version"], "3.2-nullrhi-handshake")
        self.assertEqual(payload["old_path"], "/Old/M")
        self.assertEqual(payload["new_path"], "/New/M")
        self.assertEqual(payload["scan_folder_text"], "/Game/Test")
        self.assertIs(payload["scan_entire_project"], True)
        self.assertIs(payload["auto_save"], True)
        json.dumps(payload, ensure_ascii=False)

    def test_force_save_does_not_depend_on_unreal_dirty_flag(self) -> None:
        assets = [object(), object()]

        self.assertTrue(self.core._force_save_modified_assets(assets))
        self.assertEqual(_FakeEditorAssetLibrary.calls, [(assets, False)])

    def test_helper_ready_state_ignores_partial_file_then_accepts_handshake(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ready_path = Path(directory) / "ready.json"
            ready_path.write_text("{", encoding="utf-8")
            self.assertIsNone(
                self.external.read_helper_ready_state(str(ready_path))
            )

            ready_path.write_text(
                json.dumps({"success": True, "error": ""}),
                encoding="utf-8",
            )
            self.assertEqual(
                self.external.read_helper_ready_state(str(ready_path)),
                {"success": True, "error": ""},
            )

    def test_windows_powershell_helper_is_ascii_for_ps51_compatibility(self) -> None:
        source = POWERSHELL_HELPER_PATH.read_bytes()
        self.assertTrue(source.isascii())


if __name__ == "__main__":
    unittest.main()
