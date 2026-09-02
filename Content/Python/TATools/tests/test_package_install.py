# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


PACKAGE_INSTALL_PATH = Path(__file__).resolve().parents[2] / "PackageInstall.py"


def _load_module():
    fake_unreal = types.SimpleNamespace(
        Paths=types.SimpleNamespace(
            engine_dir=lambda: "X:/FakeEngine/Engine/",
            project_content_dir=lambda: "X:/FakeProject/Content/",
        ),
        log=lambda _message: None,
        log_warning=lambda _message: None,
        log_error=lambda _message: None,
    )
    sys.modules["unreal"] = fake_unreal
    spec = importlib.util.spec_from_file_location("PackageInstall_under_test", PACKAGE_INSTALL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PackageInstallTests(unittest.TestCase):
    def test_engine_package_dir_is_switchboard_third_party(self):
        module = _load_module()
        expected = os.path.normpath(
            "X:/FakeEngine/Engine/Extras/ThirdPartyNotUE/SwitchboardThirdParty"
        )
        self.assertEqual(module._engine_package_dir(), expected)

    def test_install_targets_engine_third_party_instead_of_project(self):
        module = _load_module()
        engine_packages = str(Path(tempfile.gettempdir()) / "engine-packages")

        with (
            mock.patch.object(module, "_engine_package_dir", return_value=engine_packages),
            mock.patch.object(module, "is_package_installed", side_effect=[False, True]),
            mock.patch.object(module, "_engine_python_exe", return_value="python.exe"),
            mock.patch.object(module.subprocess, "check_call") as check_call,
        ):
            ok, _message = module.install_package("PySide6")

        self.assertTrue(ok)
        command = check_call.call_args.args[0]
        self.assertIn("--target", command)
        target_index = command.index("--target") + 1
        self.assertEqual(command[target_index], engine_packages)
        self.assertIn("PySide6_Essentials==6.5.3", command)
        self.assertNotIn("--user", command)
        self.assertEqual(sys.path[0], engine_packages)


if __name__ == "__main__":
    unittest.main()
