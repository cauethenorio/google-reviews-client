import pytest

from google_reviews_client.cli.auth import find_client_secrets_files


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestFindClientSecretsFiles:
    def test_explicit_path_exists(self, tmp_cwd):
        f = tmp_cwd / "my-secrets.json"
        f.write_text("{}")
        result = find_client_secrets_files(tmp_cwd, explicit_path=f)
        assert result == f

    def test_explicit_path_not_found(self, tmp_cwd):
        with pytest.raises(FileNotFoundError):
            find_client_secrets_files(tmp_cwd, explicit_path=tmp_cwd / "nope.json")

    def test_auto_detect_single(self, tmp_cwd):
        f = tmp_cwd / "client_secret_foo.json"
        f.write_text("{}")
        result = find_client_secrets_files(tmp_cwd)
        assert result == f

    def test_auto_detect_none(self, tmp_cwd):
        with pytest.raises(FileNotFoundError):
            find_client_secrets_files(tmp_cwd)

    def test_auto_detect_multiple(self, tmp_cwd):
        (tmp_cwd / "client_secret_a.json").write_text("{}")
        (tmp_cwd / "client_secret_b.json").write_text("{}")
        with pytest.raises(ValueError, match="Multiple"):
            find_client_secrets_files(tmp_cwd)
