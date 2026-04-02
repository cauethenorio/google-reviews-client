"""Tests for build hygiene and dependency separation (PKG-01, PKG-03)."""

import subprocess
import sys
import zipfile
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

CREDENTIAL_PATTERNS = [
    "credentials",
    "client_secret",
    "tokens.json",
    ".tokens.json",
    "reviews",
    "google-reviews-config",
    ".json.old",
    "_tokens.json",
]


class TestBuildHygiene:
    def test_no_credential_files_in_wheel(self, tmp_path):
        """Built wheel must not contain credential or data files."""
        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0, f"uv build failed: {result.stderr}"

        wheels = list(tmp_path.glob("*.whl"))
        assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)}"

        with zipfile.ZipFile(wheels[0]) as zf:
            names = zf.namelist()
            for name in names:
                basename = Path(name).name.lower()
                for pattern in CREDENTIAL_PATTERNS:
                    if pattern in basename and basename.endswith((".json", ".jsonl", ".json.old")):
                        raise AssertionError(f"Credential/data file found in wheel: {name}")


class TestDependencySeparation:
    def test_oauthlib_not_in_core_dependencies(self):
        """google-auth-oauthlib must not be a core dependency."""
        with PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        deps = config["project"]["dependencies"]
        for dep in deps:
            assert "google-auth-oauthlib" not in dep, f"google-auth-oauthlib found in core dependencies: {dep}"

    def test_oauthlib_in_cli_extra(self):
        """google-auth-oauthlib must be in [cli] optional extra."""
        with PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        cli_deps = config["project"]["optional-dependencies"]["cli"]
        oauthlib_found = any("google-auth-oauthlib" in dep for dep in cli_deps)
        assert oauthlib_found, f"google-auth-oauthlib not found in cli extra: {cli_deps}"

    def test_click_in_cli_extra(self):
        """click must be in [cli] optional extra."""
        with PYPROJECT_PATH.open("rb") as f:
            config = tomllib.load(f)
        cli_deps = config["project"]["optional-dependencies"]["cli"]
        click_found = any("click" in dep for dep in cli_deps)
        assert click_found, f"click not found in cli extra: {cli_deps}"

    def test_library_import_does_not_pull_click(self):
        """Importing the library must not import click or google_auth_oauthlib.

        Note: In the test environment both are installed, so we check
        they are not pulled in as a side effect of importing the library.
        We do this by checking that the library __init__.py itself does not
        reference click or google_auth_oauthlib.
        """
        init_path = PROJECT_ROOT / "src" / "google_reviews_client" / "__init__.py"
        content = init_path.read_text()
        assert "import click" not in content, "__init__.py must not import click"
        assert "google_auth_oauthlib" not in content, "__init__.py must not import google_auth_oauthlib"
