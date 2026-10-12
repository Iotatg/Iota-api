#!/usr/bin/env python3
"""Generate a secure ADMIN_TOKEN.

USAGE:
    python scripts/generate_admin_token.py
    python scripts/generate_admin_token.py 48   # specify length
"""
import secrets
import sys

length = int(sys.argv[1]) if len(sys.argv) > 1 else 48
print(secrets.token_urlsafe(length))
