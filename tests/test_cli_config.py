import json

import pytest

from google_reviews_client.cli.config import (
    Config,
    build_config_path,
    find_config_files,
    load_config,
    save_config,
)


@pytest.fixture
def tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def make_config_data():
    return {
        "credentials": {
            "token": "tok",
            "refresh_token": "ref",
            "client_id": "123456-xxx.apps.googleusercontent.com",
            "client_secret": "secret",
            "token_uri": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/business.manage"],
        },
        "targets": [
            {
                "account": "accounts/111",
                "account_name": "Test Account",
                "locations": [
                    {
                        "location": "locations/222",
                        "title": "Test Location",
                        "language": "pt-BR",
                    }
                ],
            }
        ],
    }


class TestFindConfigFiles:
    def test_finds_single_config(self, tmp_cwd):
        path = tmp_cwd / "google-reviews-config.123.user@test.com.json"
        path.write_text(json.dumps(make_config_data()))
        result = find_config_files(tmp_cwd)
        assert result == [path]

    def test_finds_multiple_configs(self, tmp_cwd):
        p1 = tmp_cwd / "google-reviews-config.123.a@test.com.json"
        p2 = tmp_cwd / "google-reviews-config.456.b@test.com.json"
        p1.write_text(json.dumps(make_config_data()))
        p2.write_text(json.dumps(make_config_data()))
        result = find_config_files(tmp_cwd)
        assert len(result) == 2

    def test_returns_empty_when_none(self, tmp_cwd):
        result = find_config_files(tmp_cwd)
        assert result == []

    def test_explicit_path(self, tmp_cwd):
        path = tmp_cwd / "my-config.json"
        path.write_text(json.dumps(make_config_data()))
        result = find_config_files(tmp_cwd, explicit_path=path)
        assert result == [path]

    def test_explicit_path_not_found(self, tmp_cwd):
        with pytest.raises(FileNotFoundError):
            find_config_files(tmp_cwd, explicit_path=tmp_cwd / "nope.json")


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_cwd):
        data = make_config_data()
        path = tmp_cwd / "google-reviews-config.123456.user@test.com.json"
        path.write_text(json.dumps(data))
        config = load_config(path)
        assert config.path == path
        assert config.email == "user@test.com"
        assert config.project_number == "123456"
        assert len(config.targets) == 1
        assert config.targets[0]["account"] == "accounts/111"

    def test_loads_config_without_targets(self, tmp_cwd):
        data = make_config_data()
        del data["targets"]
        path = tmp_cwd / "config.json"
        path.write_text(json.dumps(data))
        config = load_config(path)
        assert config.targets == []


class TestSaveConfig:
    def test_saves_config(self, tmp_cwd):
        config = Config(
            path=tmp_cwd / "google-reviews-config.123.user@test.com.json",
            credentials_data={
                "token": "tok",
                "client_id": "123-xxx.apps.googleusercontent.com",
            },
            targets=[],
        )
        save_config(config)
        assert config.path.exists()
        data = json.loads(config.path.read_text())
        assert "credentials" in data
        assert "targets" in data

    def test_saves_with_targets(self, tmp_cwd):
        target = {
            "account": "accounts/111",
            "account_name": "Test",
            "locations": [{"location": "locations/222", "title": "Loc"}],
        }
        config = Config(
            path=tmp_cwd / "config.json",
            credentials_data={"token": "tok", "client_id": "123-xxx"},
            targets=[target],
        )
        save_config(config)
        data = json.loads(config.path.read_text())
        assert len(data["targets"]) == 1
        assert data["targets"][0]["account_name"] == "Test"


class TestBuildConfigPath:
    def test_builds_path(self, tmp_cwd):
        result = build_config_path(tmp_cwd, "123456", "User@Test.com")
        assert result == tmp_cwd / "google-reviews-config.123456.user@test.com.json"
