# -*- coding: utf-8 -*-
import os
import subprocess
import sys


def main() -> int:
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    if not os.path.isdir(os.path.join(root, "eduplay")):
        print(f"[ERROR] Expected eduplay directory under: {root}")
        return 1

    skip_names = {
        "app.py",
        "main_window.py",
        "setup_cython.py",
        "compile_cython.py",
        # Huge Jinja/JS templates; Nuitka compiles this module instead.
        "export_service.py",
    }
    skip_mods = {"eduplay.ui.main_window", "eduplay.core.export_service"}
    found = []
    seen = set()

    for dirpath, _, files in os.walk(os.path.join(root, "eduplay")):
        for fname in sorted(files):
            if not fname.endswith(".py") or fname in skip_names:
                continue
            if ".." in fname:
                continue
            rel = os.path.relpath(os.path.join(dirpath, fname), root)
            if fname == "__init__.py" or rel == os.path.join("eduplay", "__init__.py"):
                continue
            mod = rel[:-3].replace(os.sep, ".")
            parts = mod.split(".")
            if not mod or not all(part.isidentifier() for part in parts):
                continue
            if mod in seen or mod in skip_mods:
                continue
            seen.add(mod)
            found.append((mod, os.path.join(root, rel)))

    print(f"CYTHON-MODULES= {len(found)}")
    failed = []

    for idx, (mod, src) in enumerate(found, 1):
        print(f"[cython] {idx}/{len(found)} {mod}")
        try:
            setup_code = (
                "from setuptools import setup; "
                "from Cython.Build import cythonize; "
                f"setup(ext_modules=cythonize([{src!r}], compiler_directives={{'language_level': '3'}}, quiet=True, force=True))"
            )
            result = subprocess.run(
                [sys.executable, "-c", setup_code, "build_ext", "--inplace"],
                cwd=root,
                check=False,
            )
            if result.returncode != 0:
                failed.append(mod)
        except Exception as exc:  # pragma: no cover - defensive only
            failed.append(mod)
            print(f"CYTHON-FAILED: {mod} {exc}")

    print(f"CYTHON-DONE: {len(found) - len(failed)} ok, {len(failed)} left for Nuitka")
    if failed:
        print(f"CYTHON-SKIPPED: {', '.join(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
