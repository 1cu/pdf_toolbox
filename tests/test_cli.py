"""Tests for the command line interface wrapping the action registry."""

from __future__ import annotations

import argparse
import inspect
import json
import typing as t
from pathlib import Path

import pytest

from pdf_toolbox import cli
from pdf_toolbox.actions import Action, Param


def _param(
    name: str,
    annotation: t.Any,
    default: t.Any = inspect._empty,
) -> Param:
    return Param(
        name=name,
        kind=str(inspect.Parameter.POSITIONAL_OR_KEYWORD),
        annotation=annotation,
        default=default,
    )


@pytest.fixture()
def fake_actions(monkeypatch: pytest.MonkeyPatch) -> list[Action]:
    """Provide deterministic actions for CLI tests."""

    def sample_action(
        foo: int,
        mode: t.Union[int, t.Literal["low", "high"]] = "low",
        flag: bool = False,
    ) -> dict[str, t.Any]:
        return {"foo": foo, "mode": mode, "flag": flag}

    def failing_action() -> None:
        raise RuntimeError("boom")

    def plain_action() -> None:
        return None

    def echo_action(path: Path) -> Path:
        return path

    actions = [
        Action(
            fqname="tests.cli.sample_action",
            key="sample_action",
            func=sample_action,
            params=[
                _param("foo", int),
                _param("mode", t.Union[int, t.Literal["low", "high"]], "low"),
                _param("flag", bool, False),
            ],
            help="Sample action used in CLI tests.\nAdditional detail is ignored.",
            category="Tests",
        ),
        Action(
            fqname="tests.cli.failing_action",
            key="failing_action",
            func=failing_action,
            params=[],
            help="Action that raises an error.",
            category="Tests",
        ),
        Action(
            fqname="tests.cli.echo_action",
            key="echo_action",
            func=echo_action,
            params=[_param("path", Path)],
            help="Echo the provided path.",
            category=None,
        ),
        Action(
            fqname="tests.cli.plain_action",
            key="Plain",
            func=plain_action,
            params=[],
            help="",
            category=None,
        ),
    ]

    monkeypatch.setattr(cli, "list_actions", lambda: list(actions))
    return actions


def test_list_actions_outputs_summary(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "[Tests] sample_action (Sample action)" in out
    assert "Sample action used in CLI tests." in out


def test_list_actions_can_include_fqname(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["list", "--fqname"])
    assert code == 0
    out = capsys.readouterr().out
    assert ":: tests.cli.sample_action" in out


def test_list_rejects_extra_arguments(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["list", "--category", "Tests", "--extra"])
    assert code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments" in err


def test_list_actions_filters_by_category(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["list", "--category", "Unknown"])
    assert code == 2
    err = capsys.readouterr().err
    assert "no actions found" in err


def test_describe_action_shows_parameters(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["describe", "sample_action"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Action: sample_action" in out
    assert "--foo" in out
    assert "required" in out
    assert "default='low'" in out


def test_describe_action_without_parameters(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["describe", "Plain"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Parameters: none" in out


def test_describe_unknown_action(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["describe", "missing"])
    assert code == 2
    err = capsys.readouterr().err
    assert "unknown action" in err


def test_describe_rejects_extra_arguments(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["describe", "sample_action", "--extra"])
    assert code == 2
    err = capsys.readouterr().err
    assert "unrecognized arguments" in err


def test_run_action_converts_values(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "sample_action", "--foo", "5", "--mode", "high", "--flag", "yes"])
    assert code == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"foo": 5, "mode": "high", "flag": True}


def test_run_action_reports_missing_required_argument(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "sample_action"])
    assert code == 2
    err = capsys.readouterr().err
    assert "missing required parameters" in err


def test_run_action_rejects_unknown_parameter(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "sample_action", "--foo", "3", "--extra", "value"])
    assert code == 2
    err = capsys.readouterr().err
    assert "unknown parameter" in err


def test_run_action_reports_invalid_literal(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "sample_action", "--foo", "3", "--mode", "invalid"])
    assert code == 2
    err = capsys.readouterr().err
    assert "expected one of" in err


def test_run_action_reports_invalid_boolean(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "sample_action", "--foo", "3", "--flag", "maybe"])
    assert code == 2
    err = capsys.readouterr().err
    assert "invalid boolean value" in err


def test_run_action_accepts_dash_dash_separator(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "sample_action", "--", "--foo", "4", "--mode", "2"])
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result == {"foo": 4, "mode": 2, "flag": False}


def test_run_action_handles_path_output(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "echo_action", "--path", "/tmp/example.txt"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith("/tmp/example.txt")


def test_run_action_surfaces_runtime_errors(fake_actions: list[Action], capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["run", "failing_action"])
    assert code == 1
    err = capsys.readouterr().err
    assert "Error: boom" in err


def test_main_returns_parse_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main([])
    assert code == 2
    err = capsys.readouterr().err
    assert "usage" in err.lower()


def test_main_reports_unknown_command(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    class DummyParser:
        def parse_known_args(self, argv: list[str] | None = None):
            return argparse.Namespace(command="bogus"), []

    monkeypatch.setattr(cli, "_create_parser", DummyParser)
    code = cli.main([])
    assert code == 2
    err = capsys.readouterr().err
    assert "unsupported command" in err


def test_describe_action_detects_ambiguous_name(
    fake_actions: list[Action], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    duplicate = Action(
        fqname="tests.cli.sample_action_alias",
        key="Sample action",
        func=lambda: None,
        params=[],
        help="",
        category=None,
    )
    monkeypatch.setattr(cli, "list_actions", lambda: list(fake_actions) + [duplicate])
    code = cli.main(["describe", "Sample action"])
    assert code == 2
    err = capsys.readouterr().err
    assert "ambiguous action" in err


def test_format_param_suffix_handles_empty_annotation() -> None:
    param = Param(
        name="raw",
        kind=str(inspect.Parameter.POSITIONAL_OR_KEYWORD),
        annotation=inspect._empty,
        default="value",
    )
    suffix = cli._format_param_suffix(param)
    assert "default='value'" in suffix


def test_format_param_suffix_handles_annotated_type() -> None:
    annotated = t.Annotated[int, "meta"]
    param = Param(
        name="annotated",
        kind=str(inspect.Parameter.POSITIONAL_OR_KEYWORD),
        annotation=annotated,
        default=0,
    )
    suffix = cli._format_param_suffix(param)
    assert "Annotated" in suffix


def test_parse_named_arguments_supports_equals() -> None:
    parsed = cli._parse_named_arguments(["--foo=1"])
    assert parsed == {"foo": "1"}


def test_parse_named_arguments_requires_prefix() -> None:
    with pytest.raises(cli.CliError):
        cli._parse_named_arguments(["foo"])


def test_parse_named_arguments_requires_name() -> None:
    with pytest.raises(cli.CliError):
        cli._parse_named_arguments(["--", "--"])


def test_parse_named_arguments_requires_value() -> None:
    with pytest.raises(cli.CliError):
        cli._parse_named_arguments(["--foo"])


def test_parse_named_arguments_handles_empty_value_error() -> None:
    with pytest.raises(cli.CliError):
        cli._parse_named_arguments(["--", "--foo", "1", "--", "bar"])


def test_build_call_arguments_rejects_unsupported_kind() -> None:
    action = Action(
        fqname="tests.cli.varargs",
        key="varargs",
        func=lambda *args: None,
        params=[
            Param(
                name="args",
                kind="VAR_POSITIONAL",
                annotation=int,
                default=inspect._empty,
            )
        ],
        help="",
        category=None,
    )
    with pytest.raises(cli.CliError):
        cli._build_call_arguments(action, {})


def test_convert_value_handles_empty_annotation() -> None:
    assert cli._convert_value("text", inspect._empty) == "text"


def test_convert_value_handles_float_and_errors() -> None:
    assert cli._convert_value("2.5", float) == 2.5
    with pytest.raises(cli.CliError):
        cli._convert_value("oops", float)


def test_convert_value_handles_path_subclass() -> None:
    posix_path = type(Path("/"))
    result = cli._convert_value("/tmp", posix_path)
    assert isinstance(result, posix_path)


def test_convert_value_handles_custom_class() -> None:
    class Upper(str):
        def __new__(cls, value: str):
            return str.__new__(cls, value.upper())

    result = cli._convert_value("hello", Upper)
    assert result == "HELLO"


def test_convert_literal_supports_bool_int_and_float() -> None:
    assert cli._convert_literal("true", (True, False)) is True
    assert cli._convert_literal("2", (1, 2)) == 2
    assert cli._convert_literal("1.5", (1.0, 1.5)) == 1.5
    with pytest.raises(cli.CliError):
        cli._convert_literal("x", ("a",))


def test_convert_bool_accepts_false_and_rejects_unknown() -> None:
    assert cli._convert_bool("off") is False
    with pytest.raises(cli.CliError):
        cli._convert_bool("maybe")


def test_render_result_handles_none(capsys: pytest.CaptureFixture[str]) -> None:
    cli._render_result(None)
    assert capsys.readouterr().out == ""


def test_render_result_handles_numeric_output(capsys: pytest.CaptureFixture[str]) -> None:
    cli._render_result(7)
    assert capsys.readouterr().out.strip() == "7"
