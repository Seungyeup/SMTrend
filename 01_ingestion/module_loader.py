"""숫자로 시작하는 폴더를 안전한 별칭 패키지로 로드한다."""

import importlib.util
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_package(alias, folder_name):
    """숫자 prefix 폴더를 import 가능한 패키지 별칭으로 로드한다."""
    loaded = sys.modules.get(alias)
    if loaded is not None:
        return loaded

    package_init = BASE_DIR / folder_name / "__init__.py"
    if not package_init.exists():
        raise ModuleNotFoundError(f"Package folder not found: {folder_name}")

    spec = importlib.util.spec_from_file_location(
        alias,
        package_init,
        submodule_search_locations=[str(package_init.parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load package spec for: {folder_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module
