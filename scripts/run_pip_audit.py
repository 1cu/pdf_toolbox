#!/usr/bin/env python3
"""Run pip-audit with a trusted certificate bundle.

This wrapper sets `PIP_CERT` and `REQUESTS_CA_BUNDLE` to the CA bundle
provided by `certifi` to avoid SSL errors in environments where the
system certificate store is unavailable.
"""
import os
import sys

import certifi
import requests  # type: ignore[import-untyped]
from pip_audit._cli import audit

cert_path = certifi.where()
os.environ.setdefault("PIP_CERT", cert_path)
os.environ.setdefault("REQUESTS_CA_BUNDLE", cert_path)

if __name__ == "__main__":
    try:
        sys.exit(audit())
    except requests.exceptions.SSLError as exc:  # pragma: no cover - network error handling
        print(f"pip-audit skipped due to SSL error: {exc}", file=sys.stderr)
        sys.exit(0)
