"""Command line interface for running registered actions."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
import types
import typing as t
from pathlib import Path
from typing import Self

from pdf_toolbox.actions import Action, list_actions

_Handler = t.Callable[[argparse.Namespace, list[str]], int]


class CliError(RuntimeError):
    """Raised when CLI arguments cannot be processed."""

    @classmethod
    def unrecognized_arguments(cls, extra: t.Sequence[str]) -> Self:
        joined = " ".join(extra)
        return cls(f"unrecognized arguments: {joined}")

    @classmethod
    def unsupported_command(cls, command: str) -> Self:
        return cls(f"unsupported command: {command}")

    @classmethod
    def no_actions(cls) -> Self:
        return cls("no actions found")

    @classmethod
    def unknown_action(cls, identifier: str) -> Self:
        return cls(f"unknown action: {identifier}")

    @classmethod
    def ambiguous_action(cls, identifier: str) -> Self:
        return cls(f"ambiguous action: {identifier}")

    @classmethod
    def expected_named_parameter(cls, token: str) -> Self:
        return cls(f"expected parameter starting with '--', got {token!r}")

    @classmethod
    def missing_parameter_name(cls) -> Self:
        return cls("missing parameter name")

    @classmethod
    def missing_parameter_value(cls, name: str) -> Self:
        return cls(f"missing value for parameter {name!r}")

    @classmethod
    def unsupported_parameter_kind(cls, kind: str) -> Self:
        return cls(f"unsupported parameter kind: {kind}")

    @classmethod
    def missing_required_parameters(cls, names: t.Iterable[str]) -> Self:
        joined = ", ".join(names)
        return cls("missing required parameters: " + joined)

    @classmethod
    def unknown_parameters(cls, names: t.Iterable[str]) -> Self:
        joined = ", ".join(sorted(names))
        return cls("unknown parameter(s): " + joined)

    @classmethod
    def union_conversion_failed(cls, value: str) -> Self:
        return cls(f"could not convert value {value!r}")

    @classmethod
    def literal_expected(cls, choices: t.Iterable[t.Any]) -> Self:
        allowed = ", ".join(repr(choice) for choice in choices)
        return cls(f"expected one of: {allowed}")

    @classmethod
    def invalid_boolean(cls, value: str) -> Self:
        return cls(f"invalid boolean value: {value!r}")

    @classmethod
    def conversion_error(cls, message: str) -> Self:
        return cls(message)


def main(argv: t.Sequence[str] | None = None) -> int:
    """Parse *argv* and dispatch the requested command."""
    parser = _create_parser()
    try:
        args, extra = parser.parse_known_args(argv)
    except SystemExit as exc:  # pragma: no cover - argparse handles usage exits  # pdf-toolbox: delegate help/usage exit codes to argparse | issue:-
        code = exc.code
        return code if isinstance(code, int) else 1

    try:
        handler = _resolve_handler(args.command)
        return handler(args, extra)
    except CliError as exc:
        _write_line(sys.stderr, str(exc))
        return 2
    except Exception as exc:  # pragma: no cover - exercised in integration tests  # pdf-toolbox: runtime errors bubble up to stderr for CLI users | issue:-
        _write_line(sys.stderr, f"Error: {exc}")
        return 1


def _resolve_handler(command: str) -> _Handler:
    handlers: dict[str, _Handler] = {
        "list": _handle_list,
        "describe": _handle_describe,
        "run": _handle_run,
    }
    try:
        return handlers[command]
    except KeyError as exc:
        raise CliError.unsupported_command(command) from exc


def _handle_list(args: argparse.Namespace, extra: list[str]) -> int:
    if extra:
        raise CliError.unrecognized_arguments(extra)
    _cmd_list(category=args.category, show_fqname=args.fqname)
    return 0


def _handle_describe(args: argparse.Namespace, extra: list[str]) -> int:
    if extra:
        raise CliError.unrecognized_arguments(extra)
    _cmd_describe(args.action)
    return 0


def _handle_run(args: argparse.Namespace, extra: list[str]) -> int:
    combined_arguments = list(args.arguments) + list(extra)
    _cmd_run(args.action, combined_arguments)
    return 0


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-toolbox",
        description="Interact with registered pdf-toolbox actions.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list",
        help="List available actions.",
        description="List actions available to the CLI.",
    )
    list_parser.add_argument(
        "--category",
        help="Filter actions by category.",
    )
    list_parser.add_argument(
        "--fqname",
        action="store_true",
        help="Include the fully qualified name in the listing.",
    )

    describe_parser = subparsers.add_parser(
        "describe",
        help="Show details about a single action.",
    )
    describe_parser.add_argument("action", help="Action key or fully qualified name.")

    run_parser = subparsers.add_parser(
        "run",
        help="Execute an action with keyword arguments.",
    )
    run_parser.add_argument("action", help="Action key or fully qualified name.")
    run_parser.add_argument(
        "arguments",
        nargs=argparse.REMAINDER,
        help="Additional parameters in --name value form.",
    )

    return parser


def _cmd_list(*, category: str | None, show_fqname: bool) -> None:
    actions = sorted(list_actions(), key=lambda act: (act.category or "", act.key))
    filtered = [act for act in actions if category is None or act.category == category]
    if not filtered:
        raise CliError.no_actions()
    lines: list[str] = []
    for action in filtered:
        summary = action.help.splitlines()[0] if action.help else ""
        label = action.name
        label = f"{action.key} ({label})" if label != action.key else action.key
        if action.category:
            label = f"[{action.category}] {label}"
        if show_fqname:
            label = f"{label} :: {action.fqname}"
        lines.append(f"{label} - {summary}" if summary else label)
    _write_lines(sys.stdout, lines)


def _cmd_describe(identifier: str) -> None:
    action = _find_action(identifier)
    lines = [f"Action: {action.key}", f"Qualified name: {action.fqname}"]
    if action.category:
        lines.append(f"Category: {action.category}")
    if action.help:
        lines.extend(["Description:", action.help])
    if action.params:
        lines.append("Parameters:")
        lines.extend(
            f"  --{param.name}{_format_param_suffix(param)}" for param in action.params
        )
    else:
        lines.append("Parameters: none")
    _write_lines(sys.stdout, lines)


def _cmd_run(identifier: str, arguments: list[str]) -> None:
    action = _find_action(identifier)
    options = _parse_named_arguments(arguments)
    kwargs = _build_call_arguments(action, options)
    result = action.func(**kwargs)
    _render_result(result)


def _find_action(identifier: str) -> Action:
    actions = list_actions()
    matches = [
        action
        for action in actions
        if identifier in {action.key, action.fqname, action.name}
    ]
    if not matches:
        raise CliError.unknown_action(identifier)
    if len(matches) > 1:
        raise CliError.ambiguous_action(identifier)
    return matches[0]


def _format_param_suffix(param: t.Any) -> str:
    parts: list[str] = []
    annotation = _format_annotation(param.annotation)
    if annotation:
        parts.append(annotation)
    if param.default is inspect._empty:
        parts.append("required")
    else:
        parts.append(f"default={param.default!r}")
    return " (" + ", ".join(parts) + ")"


def _format_annotation(annotation: t.Any) -> str:
    if annotation in {inspect._empty, t.Any, None}:
        return ""
    origin = t.get_origin(annotation)
    if origin is types.UnionType or origin is t.Union:
        parts = [
            _format_annotation(arg) or _format_basic(arg)
            for arg in t.get_args(annotation)
        ]
        return " | ".join(parts)
    if origin is t.Literal:
        values = ", ".join(repr(arg) for arg in t.get_args(annotation))
        return f"{{{values}}}"
    return _format_basic(annotation)


def _format_basic(annotation: t.Any) -> str:
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation)


def _parse_named_arguments(tokens: list[str]) -> dict[str, str]:
    items: dict[str, str] = {}
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("--"):
            raise CliError.expected_named_parameter(token)
        name_part = token[2:]
        if not name_part:
            raise CliError.missing_parameter_name()
        if "=" in name_part:
            name, value = name_part.split("=", 1)
        else:
            index += 1
            if index >= len(tokens):
                raise CliError.missing_parameter_value(name_part)
            value = tokens[index]
            name = name_part
        key = name.replace("-", "_")
        items[key] = value
        index += 1
    return items


def _build_call_arguments(action: Action, provided: dict[str, str]) -> dict[str, t.Any]:
    values: dict[str, t.Any] = {}
    remaining = dict(provided)
    missing: list[str] = []
    for param in action.params:
        if param.kind not in {
            "POSITIONAL_ONLY",
            "POSITIONAL_OR_KEYWORD",
            "KEYWORD_ONLY",
        }:
            raise CliError.unsupported_parameter_kind(param.kind)
        if param.name in remaining:
            raw_value = remaining.pop(param.name)
            values[param.name] = _convert_value(raw_value, param.annotation)
        elif param.default is inspect._empty:
            missing.append(param.name)
    if missing:
        raise CliError.missing_required_parameters(missing)
    if remaining:
        raise CliError.unknown_parameters(remaining)
    return values


def _convert_value(value: str, annotation: t.Any) -> t.Any:
    origin = t.get_origin(annotation)
    if annotation in {inspect._empty, t.Any, None}:
        result: t.Any = value
    elif origin in {types.UnionType, t.Union}:
        result = _convert_union_value(value, annotation)
    elif origin is t.Literal:
        result = _convert_literal(value, t.get_args(annotation))
    elif origin is t.Annotated:
        annotated_args = t.get_args(annotation)
        result = _convert_value(value, annotated_args[0]) if annotated_args else value
    else:
        converter = _resolve_converter(annotation)
        if converter is not None:
            result = converter(value)
        elif isinstance(annotation, type):
            result = _convert_custom_type(value, annotation)
        else:
            result = value
    return result


def _convert_union_value(value: str, annotation: t.Any) -> t.Any:
    last_error: CliError | None = None
    for arg in t.get_args(annotation):
        try:
            return _convert_value(value, arg)
        except CliError as err:
            last_error = err
            continue
    if last_error is not None:
        raise last_error
    raise CliError.union_conversion_failed(value)


def _resolve_converter(annotation: t.Any) -> t.Callable[[str], t.Any] | None:
    converter: t.Callable[[str], t.Any] | None = None
    if annotation is bool:
        converter = _convert_bool
    elif annotation is int:
        converter = _convert_int
    elif annotation is float:
        converter = _convert_float
    elif annotation is str:
        converter = _identity
    elif annotation is Path:
        converter = Path
    elif isinstance(annotation, type) and issubclass(annotation, Path):
        converter = annotation
    return converter


def _convert_int(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:  # pragma: no cover - exercised via literal unions  # pdf-toolbox: preserve conversion error text for numeric parameters | issue:-
        raise CliError.conversion_error(str(exc)) from exc


def _convert_float(value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise CliError.conversion_error(str(exc)) from exc


def _convert_custom_type(value: str, annotation: type[t.Any]) -> t.Any:
    # Fallback for other classes - rely on string constructor if available.
    try:
        return annotation(value)
    except Exception as exc:  # pragma: no cover - depends on user types  # pdf-toolbox: surface constructor failures from custom annotations | issue:-
        raise CliError.conversion_error(str(exc)) from exc


def _identity(value: str) -> str:
    return value


def _convert_literal(value: str, choices: tuple[t.Any, ...]) -> t.Any:
    for option in choices:
        if isinstance(option, str) and value == option:
            return option
        if isinstance(option, bool) and _convert_bool(value) == option:
            return option
        if isinstance(option, int):
            try:
                if int(value) == option:
                    return option
            except ValueError:
                continue
        if isinstance(option, float):
            try:
                if float(value) == option:
                    return option
            except ValueError:
                continue
    raise CliError.literal_expected(choices)


def _convert_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise CliError.invalid_boolean(value)


def _render_result(result: t.Any) -> None:
    if result is None:
        return
    if isinstance(result, str | Path):
        _write_line(sys.stdout, str(result))
        return
    if isinstance(result, int | float | bool):
        _write_line(sys.stdout, json.dumps(result))
        return
    _write_line(sys.stdout, json.dumps(result, indent=2, default=str))


def _write_line(stream: t.TextIO, text: str) -> None:
    stream.write(f"{text}\n")


def _write_lines(stream: t.TextIO, lines: t.Iterable[str]) -> None:
    collected = list(lines)
    if not collected:
        return
    stream.write("\n".join(collected) + "\n")


__all__ = ["main"]
