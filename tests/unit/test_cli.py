import yaml
import pytest

from vault_cli import cli
from vault_cli import client


class FakeClient(client.VaultClientBase):
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        print(kwargs)

    def get_secret(self, path):
        return "bar"

    def list_secrets(self, path):
        return ["foo", "baz"]

    def set_secret(self, path, value):
        self.set = [path, value]

    def delete_secret(self, path):
        self.deleted = path


@pytest.fixture
def backend(mocker):
    backend = FakeClient()
    mocker.patch("vault_cli.requests.RequestsVaultClient",
                 return_value=backend)
    yield backend


def test_bad_backend(cli_runner, backend):
    result = cli_runner.invoke(cli.cli, ["--backend", "bad", "list"])

    assert result.exit_code != 0
    assert "Error: Wrong backend value bad" in result.output


def test_options(cli_runner, mocker):
    func = mocker.patch("vault_cli.client.get_client_from_kwargs")
    mocker.patch("vault_cli.settings.read_file",
                 side_effect=lambda x: "content of {}".format(x))
    result = cli_runner.invoke(cli.cli, [
        "--backend", "requests",
        "--base-path", "bla",
        "--certificate-file", "a",
        "--password-file", "b",
        "--token-file", "c",
        "--url", "https://foo",
        "--username", "user",
        "--verify",
        "list"
    ])

    assert result.exit_code == 0, result.output
    _, kwargs = func.call_args
    assert set(kwargs) == {
        "backend",
        "base_path",
        "certificate",
        "password",
        "token",
        "url",
        "username",
        "verify",
    }
    assert kwargs["base_path"] == "bla"
    assert kwargs["certificate"] == "content of a"
    assert kwargs["password"] == "content of b"
    assert kwargs["token"] == "content of c"
    assert kwargs["url"] == "https://foo"
    assert kwargs["username"] == "user"
    assert kwargs["verify"] is True


def test_list(cli_runner, backend):
    result = cli_runner.invoke(cli.cli, ["list"])

    assert result.output == "foo\nbaz\n"
    assert result.exit_code == 0


def test_get_text(cli_runner, backend):

    result = cli_runner.invoke(cli.cli, ["get", "a", "--text"])

    assert result.output == "bar\n"
    assert result.exit_code == 0


def test_get_yaml(cli_runner, backend):
    result = cli_runner.invoke(cli.cli, ["get", "a"])

    assert yaml.safe_load(result.output) == "bar"
    assert result.exit_code == 0


def test_get_all(cli_runner, backend):

    result = cli_runner.invoke(cli.cli, ["get-all", "a"])

    assert yaml.safe_load(result.output) == {'a': {'baz': 'bar', 'foo': 'bar'}}
    assert result.exit_code == 0


def test_set(cli_runner, backend):

    result = cli_runner.invoke(cli.cli, ["set", "a", "b"])

    assert result.exit_code == 0
    assert backend.set == ["a", "b"]


def test_set_list(cli_runner, backend):

    result = cli_runner.invoke(cli.cli, ["set", "a", "b", "c"])

    assert result.exit_code == 0
    assert backend.set == ["a", ["b", "c"]]


def test_set_yaml(cli_runner, backend):

    result = cli_runner.invoke(cli.cli, ["set", "--yaml", "a", '{"b": "c"}'])

    assert result.exit_code == 0
    assert backend.set == ["a", {"b": "c"}]


def test_delete(cli_runner, backend):

    result = cli_runner.invoke(cli.cli, ["delete", "a"])

    assert result.exit_code == 0
    assert backend.deleted == "a"


def test_main(mocker):
    mock_cli = mocker.patch("vault_cli.cli.cli")
    environ = mocker.patch("os.environ", {})

    cli.main()

    mock_cli.assert_called_with()
    assert environ == {"LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
