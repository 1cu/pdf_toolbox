"""Command line interface for running registered actions."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
import types
import typing as t
from pathlib import Path

from pdf_toolbox.actions import Action, list_actions


class CliError(RuntimeError):
    """Raised when CLI arguments cannot be processed."""


def main(argv: t.Sequence[str] | None = None) -> int:
    """Parse *argv* and dispatch the requested command."""

    parser = _create_parser()
    try:
        args, extra = parser.parse_known_args(argv)
    except SystemExit as exc:  # pragma: no cover - argparse handles usage exits  # pdf-toolbox: delegate help/usage exit codes to argparse | issue:-
        code = exc.code
        return code if isinstance(code, int) else 1

    try:
        if args.command == "list":
            if extra:
                raise CliError(f"unrecognized arguments: {' '.join(extra)}")
            _cmd_list(category=args.category, show_fqname=args.fqname)
            return 0
        if args.command == "describe":
            if extra:
                raise CliError(f"unrecognized arguments: {' '.join(extra)}")
            _cmd_describe(args.action)
            return 0
        if args.command == "run":
            _cmd_run(args.action, args.arguments + extra)
            return 0
        raise CliError(f"unsupported command: {args.command}")
    except CliError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - exercised in integration tests  # pdf-toolbox: runtime errors bubble up to stderr for CLI users | issue:-
        print(f"Error: {exc}", file=sys.stderr)
        return 1


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
        raise CliError("no actions found")
    for action in filtered:
        summary = action.help.splitlines()[0] if action.help else ""
        label = action.name
        if label != action.key:
            label = f"{action.key} ({label})"
        else:
            label = action.key
        if action.category:
            label = f"[{action.category}] {label}"
        if show_fqname:
            label = f"{label} :: {action.fqname}"
        if summary:
            print(f"{label} - {summary}")
        else:
            print(label)


def _cmd_describe(identifier: str) -> None:
    action = _find_action(identifier)
    print(f"Action: {action.key}")
    print(f"Qualified name: {action.fqname}")
    if action.category:
        print(f"Category: {action.category}")
    if action.help:
        print("\n".join(["Description:", action.help]))
    params_header_printed = False
    for param in action.params:
        if not params_header_printed:
            print("Parameters:")
            params_header_printed = True
        print(f"  --{param.name}{_format_param_suffix(param)}")
    if not params_header_printed:
        print("Parameters: none")


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
        raise CliError(f"unknown action: {identifier}")
    if len(matches) > 1:
        raise CliError(f"ambiguous action: {identifier}")
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
        parts = [_format_annotation(arg) or _format_basic(arg) for arg in t.get_args(annotation)]
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
            raise CliError(f"expected parameter starting with '--', got {token!r}")
        name_part = token[2:]
        if not name_part:
            raise CliError("missing parameter name")
        if "=" in name_part:
            name, value = name_part.split("=", 1)
        else:
            index += 1
            if index >= len(tokens):
                raise CliError(f"missing value for parameter {name_part!r}")
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
        if param.kind not in {"POSITIONAL_ONLY", "POSITIONAL_OR_KEYWORD", "KEYWORD_ONLY"}:
            raise CliError(f"unsupported parameter kind: {param.kind}")
        if param.name in remaining:
            raw_value = remaining.pop(param.name)
            values[param.name] = _convert_value(raw_value, param.annotation)
        elif param.default is inspect._empty:
            missing.append(param.name)
    if missing:
        raise CliError("missing required parameters: " + ", ".join(missing))
    if remaining:
        raise CliError("unknown parameter(s): " + ", ".join(sorted(remaining)))
    return values


def _convert_value(value: str, annotation: t.Any) -> t.Any:
    origin = t.get_origin(annotation)
    if annotation in {inspect._empty, t.Any, None}:
        return value
    if origin is types.UnionType or origin is t.Union:
        last_error: CliError | None = None
        for arg in t.get_args(annotation):
            try:
                return _convert_value(value, arg)
            except CliError as err:
                last_error = err
                continue
        if last_error is not None:
            raise last_error
        raise CliError(f"could not convert value {value!r}")
    if origin is t.Literal:
        return _convert_literal(value, t.get_args(annotation))
    if annotation is bool:
        return _convert_bool(value)
    if annotation is int:
        try:
            return int(value)
        except ValueError as exc:  # pragma: no cover - exercised via literal unions  # pdf-toolbox: preserve conversion error text for numeric parameters | issue:-
            raise CliError(str(exc)) from exc
    if annotation is float:
        try:
            return float(value)
        except ValueError as exc:
            raise CliError(str(exc)) from exc
    if annotation is Path:
        return Path(value)
    if isinstance(annotation, type) and issubclass(annotation, Path):
        return annotation(value)
    if isinstance(annotation, type) and annotation is str:
        return value
    if isinstance(annotation, type):
        # Fallback for other classes – rely on string constructor if available.
        try:
            return annotation(value)
        except Exception as exc:  # pragma: no cover - depends on user types  # pdf-toolbox: surface constructor failures from custom annotations | issue:-
            raise CliError(str(exc)) from exc
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
    allowed = ", ".join(repr(choice) for choice in choices)
    raise CliError(f"expected one of: {allowed}")


def _convert_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise CliError(f"invalid boolean value: {value!r}")


def _render_result(result: t.Any) -> None:
    if result is None:
        return
    if isinstance(result, (str, Path)):
        print(result)
        return
    if isinstance(result, (int, float, bool)):
        print(json.dumps(result))
        return
    print(json.dumps(result, indent=2, default=str))


__all__ = ["main"]
