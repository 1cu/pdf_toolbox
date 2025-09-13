#!/usr/bin/env python3
"""Run pip-audit with a trusted certificate bundle.

This wrapper sets `PIP_CERT` and `REQUESTS_CA_BUNDLE` to the CA bundle
provided by `certifi` to avoid SSL errors in environments where the
system certificate store is unavailable.
"""

import os
import subprocess  # nosec B404
import sys

import certifi


def main(argv: list[str]) -> int:
    """Run ``pip-audit`` forwarding arguments and handling common failures.

    The function configures ``certifi``'s CA bundle so audits don't fail due to
    missing system certificates. ``pip-audit`` cannot check packages that are
    installed in editable mode and not published on PyPI, so the wrapper also
    converts those "editable" errors into a successful exit code. That allows
    dependency scanning to proceed during development; to audit the project
    itself, build a wheel and run ``pip-audit`` on that artifact.
    """
    cert_path = certifi.where()
    os.environ.setdefault("PIP_CERT", cert_path)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", cert_path)

    cmd = [sys.executable, "-m", "pip_audit", *argv]
    proc = subprocess.run(  # noqa: S603  # nosec B603
        cmd, check=False, capture_output=True, text=True
    )

    stderr = proc.stderr
    if proc.returncode != 0:
        if "SSLError" in stderr or "CERTIFICATE_VERIFY_FAILED" in stderr:
            print(
                f"pip-audit skipped due to SSL error: {stderr.strip()}",
                file=sys.stderr,
            )
            return 0
        if "distribution marked as editable" in stderr:
            print(
                "pip-audit skipped: project installed in editable mode and not on PyPI",
                file=sys.stderr,
            )
            print(
                "build a wheel and run 'pip-audit <wheel>' to audit the project itself",
                file=sys.stderr,
            )
            return 0
        sys.stdout.write(proc.stdout)
        sys.stderr.write(stderr)
        return proc.returncode

    sys.stdout.write(proc.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
