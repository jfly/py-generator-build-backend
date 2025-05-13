import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shlex
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import Any, Type, TypeVar, get_args, get_origin

import platformdirs
import pyproject_hooks
from expandvars import expand
from packaging.requirements import Requirement

__all__ = [
    "get_caller",
]


def type_matches(val: Any, t: Type) -> bool:
    """
    Basically a version of `isinstance` that can handle "parameterized generics" (like `list[str]`).
    """
    origin = get_origin(t)
    if not origin:
        return isinstance(val, t)

    # The "origin" of something like `list[str]` is `list`.
    if not isinstance(val, origin):
        return False

    if origin is list:
        args = get_args(t)
        assert isinstance(val, list)
        assert len(args) == 1, f"We don't support runtime typechecking of type: {t}"

        (arg,) = args
        for v in val:
            if not type_matches(v, arg):
                return False

        return True

    assert False, f"We don't support runtime typechecking of type: {t}"


class KeyNotFound(KeyError):
    pass


class ExpectedDictionary(KeyError):
    pass


class WrongType(KeyError):
    pass


T = TypeVar("T")


def deep_get(
    data: Any, traversed: list[str], remaining: list[str], expected_type: Type[T]
) -> T:
    pretty_traversed = ".".join(traversed) or "."

    if len(remaining) == 0:
        if type_matches(data, expected_type):
            return data

        raise WrongType(
            f"Value at {pretty_traversed} is not of expected type {expected_type}: {data}"
        )

    if not isinstance(data, dict):
        raise ExpectedDictionary(f"Expected a dictionary at {pretty_traversed}: {data}")

    key, *rest = remaining
    if key not in data:
        raise KeyNotFound(f"Could not find {key!r} at {pretty_traversed}: {data}")

    return deep_get(data[key], [*traversed, key], rest, expected_type)


def get_required_section(pyproject: Any, key: str, expected_type: Type[T]) -> T:
    return deep_get(pyproject, [], key.split("."), expected_type)


D = TypeVar("D")


def get_optional_section(
    pyproject: Any, key: str, expected_type: Type[T], default: D
) -> T | D:
    try:
        return get_required_section(pyproject, key, expected_type)
    except KeyNotFound:
        return default


def get_current_package_name() -> str:
    # Convert the current module name from something like `py_generator_build_backend.util`
    # to an "import package" name like `py_generator_build_backend`.
    spec = importlib.util.find_spec(__name__)
    assert spec is not None
    assert spec.parent is not None
    return spec.parent


def requirement_is_current_package(requirement: str) -> bool:
    package_name = get_current_package_name()

    # Find all the "distribution packages" that provide this "import package".
    distributions = importlib.metadata.packages_distributions()[package_name]

    # Check if the given requirement (something like `py-generator-build-backend >= x.y.z`) is
    # for the package this file is a part of.
    req = Requirement(requirement)
    return req.name in distributions


def generate_project(project_root: Path, out_path: Path):
    pyproject_toml = project_root / "pyproject.toml"
    with pyproject_toml.open("rb") as f:
        pyproject = tomllib.load(f)

    with (
        tempfile.TemporaryDirectory() as tempdir,
    ):
        tmp_out_path = Path(tempdir) / "out"
        child_env = {
            **os.environ,
            "GENERATOR_OUT_PATH": str(tmp_out_path),
        }
        generator = get_required_section(
            pyproject, "tools.py-generator-build-backend.generator", str
        )
        args = shlex.split(expand(generator, nounset=True, environ=child_env))

        subprocess.run(args=args, env=child_env, cwd=project_root, check=True)

        generated_pyproject_toml = tmp_out_path / "pyproject.toml"
        with generated_pyproject_toml.open("rb") as f:
            generated_pyproject = tomllib.load(f)

        # Verify that the generated `build-system.requires` is in sync with our project's hand-written `build-system.requires`.
        # Unfortunately, users just have to manually keep these in sync (it shouldn't change often for a given project).
        build_system_requires = set(
            r
            for r in get_required_section(pyproject, "build-system.requires", list[str])
            if not requirement_is_current_package(r)
        )
        generated_build_system_requires = set(
            get_required_section(
                generated_pyproject, "build-system.requires", list[str]
            )
        )
        if build_system_requires != generated_build_system_requires:
            missing_requires = generated_build_system_requires - build_system_requires
            extra_requires = build_system_requires - generated_build_system_requires
            assert False, f"The generated `build-system.requires` is out of sync with your project's `build-system.requires`. You must update your `pyproject.toml` accordingly. Missing requires: {missing_requires}, extra requires: {extra_requires}"

        # Ensure the parent of `out_path` exists.
        out_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_out_path.rename(out_path)


def hash_dir(key: "hashlib._Hash", root: Path):
    for dirpath, dirnames, filenames in root.walk():
        relpath = dirpath.relative_to(root)
        for dirname in dirnames:
            d = relpath / dirname
            key.update(str(d).encode())

        for filename in filenames:
            path = relpath / filename
            with path.open("rb") as f:
                hashlib.file_digest(f, lambda: key)


def cached_generate_project() -> Path:
    # From https://peps.python.org/pep-0517/#config-settings:
    # > All hooks are run with working directory set to the root of the source tree
    project_root = Path.cwd().absolute()

    # Compute a "key" for the generated project by hashing together the contents of the
    # entire project directory, along with all environment variables (which can be interpolated into the `generator` we run).
    # This does a pretty good job of capturing all the "inputs" that go into generating the package, but it's not perfect:
    # the generator could be non-deterministic, or packages could be updated in the `PATH`. If you care about things like this, consider adopting a hermetic build tool like nix.
    key = hashlib.sha256()
    hash_dir(key, project_root)
    key.update(json.dumps(dict(os.environ)).encode())

    cache_dir = Path(platformdirs.user_cache_dir(get_current_package_name()))
    cached_result = cache_dir / "generated" / key.hexdigest()

    if cached_result.exists():
        print(f"Using cached generated project at {cached_result}")
    else:
        generate_project(project_root, cached_result)
        assert cached_result.is_dir()

    return cached_result


def get_caller() -> pyproject_hooks.BuildBackendHookCaller:
    generated_root = cached_generate_project()
    generated_pyproject_toml = generated_root / "pyproject.toml"
    with generated_pyproject_toml.open("rb") as f:
        generated_pyproject = tomllib.load(f)

    return pyproject_hooks.BuildBackendHookCaller(
        source_dir=str(generated_root),
        build_backend=get_required_section(
            generated_pyproject, "build-system.build-backend", str
        ),
        backend_path=get_optional_section(
            generated_pyproject, "build-system.backend-path", str, default=None
        ),
    )
