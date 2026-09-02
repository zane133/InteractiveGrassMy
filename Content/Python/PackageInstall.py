# -*- coding: utf-8 -*-
"""
Install PyPI packages into Unreal Engine's SwitchboardThirdParty directory using
the engine's bundled Python interpreter and the Tsinghua PyPI mirror.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import os
import platform
import subprocess
import sys
from typing import Tuple

import unreal

TSINGHUA_MIRROR = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
UE_5_8_PACKAGE_REQUIREMENTS = {
    "pyside6": "PySide6_Essentials==6.5.3",
}


def _engine_package_dir() -> str:
    """Return UE 5.8.1's machine-local third-party Python package directory."""
    return os.path.normpath(
        os.path.join(
            unreal.Paths.engine_dir(),
            "Extras",
            "ThirdPartyNotUE",
            "SwitchboardThirdParty",
        )
    )


def _activate_engine_package_dir() -> str:
    """Put the engine-local packages before the project's Content/Python path."""
    package_dir = _engine_package_dir()
    normalized = os.path.normcase(os.path.normpath(package_dir))
    sys.path[:] = [
        path
        for path in sys.path
        if os.path.normcase(os.path.normpath(path)) != normalized
    ]
    sys.path.insert(0, package_dir)
    return package_dir


def is_package_installed(package_name: str) -> bool:
    package_dir = _activate_engine_package_dir()
    importlib.invalidate_caches()
    spec = importlib.machinery.PathFinder.find_spec(package_name, [package_dir])
    if spec is None:
        return False
    try:
        importlib.import_module(package_name)
        return True
    except (ImportError, OSError):
        return False


def _engine_python_exe() -> str:
    engine_path = unreal.Paths.engine_dir()
    if platform.system() == "Windows":
        plat_dir = "Win64"
        exe_name = "python.exe"
    elif platform.system() == "Darwin":
        plat_dir = "Mac"
        exe_name = "python"
    else:
        plat_dir = "Linux"
        exe_name = "python"

    python_path = os.path.join(
        engine_path, "Binaries", "ThirdParty", "Python3", plat_dir, exe_name
    )
    if os.path.isfile(python_path):
        return python_path
    return sys.executable


def install_package(package_name: str, pip_name: str | None = None) -> Tuple[bool, str]:
    """
    尝试安装指定的 Python 包。

    Args:
        package_name: 导入时使用的包名 (例如 "PIL" 用于 Pillow)
        pip_name: pip 安装时使用的名称 (默认与 package_name 相同)

    Returns:
        (成功标志, 消息)
    """
    if pip_name is None:
        pip_name = package_name
    pip_requirement = UE_5_8_PACKAGE_REQUIREMENTS.get(pip_name.casefold(), pip_name)

    package_dir = _activate_engine_package_dir()
    if is_package_installed(package_name):
        return True, f"{package_name} 已安装（UE 5.8.1：{package_dir}）"

    unreal.log_warning(f"未找到 {package_name} 包，尝试安装...")

    python_exe = _engine_python_exe()

    try:
        subprocess.check_call(
            [
                python_exe,
                "-m",
                "pip",
                "install",
                pip_requirement,
                "--target",
                package_dir,
                "-i",
                TSINGHUA_MIRROR,
            ]
        )

        importlib.invalidate_caches()
        if is_package_installed(package_name):
            return True, f"{package_name} 安装成功（UE 5.8.1：{package_dir}）"
        return False, f"{package_name} 安装失败"

    except subprocess.CalledProcessError as exc:
        return False, f"安装过程中发生错误: {exc}"
    except Exception as exc:
        return False, f"发生未知错误: {exc}"


def install_packages(required_packages: list[tuple[str, str]]) -> None:
    """
    Ensure each (pip_name, import_name) pair is importable.

    Raises RuntimeError if any package fails to install.
    """
    for pip_name, import_name in required_packages:
        ok, message = install_package(import_name, pip_name)
        if ok:
            unreal.log(f"[PackageInstall] {message}")
        else:
            unreal.log_error(f"[PackageInstall] {message}")
            raise RuntimeError(message)
