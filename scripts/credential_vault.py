#!/usr/bin/env python3
"""
Credential vault — encrypt/decrypt API keys and secrets at rest using NaCl.

Uses XChaCha20-Poly1305 secretbox (symmetric authenticated encryption).
The vault key is derived from a passphrase via Argon2id.

Usage:
    # First time — set a vault passphrase
    export VAULT_PASSPHRASE="your-strong-passphrase"

    # Encrypt a credential
    python scripts/credential_vault.py encrypt KUCOIN_API_KEY "683b30f36025980001ef4bde"

    # Decrypt a credential
    python scripts/credential_vault.py decrypt KUCOIN_API_KEY

    # List stored credentials (names only, not values)
    python scripts/credential_vault.py list

    # Export all as env vars (for sourcing)
    python scripts/credential_vault.py export
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from nacl.secret import SecretBox
    from nacl.pwhash import argon2id
    from nacl.utils import random as nacl_random

    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

VAULT_DIR = Path(__file__).resolve().parent.parent / "bridge" / "vault"
VAULT_FILE = VAULT_DIR / "credentials.vault.json"
SALT_FILE = VAULT_DIR / ".vault_salt"


def _ensure_nacl():
    if not NACL_AVAILABLE:
        print("pynacl not installed. Run: pip install pynacl", file=sys.stderr)
        sys.exit(1)


def _get_passphrase() -> str:
    passphrase = os.environ.get("VAULT_PASSPHRASE", "")
    if not passphrase:
        print("Set VAULT_PASSPHRASE environment variable", file=sys.stderr)
        sys.exit(1)
    return passphrase


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return argon2id.kdf(
        SecretBox.KEY_SIZE,
        passphrase.encode("utf-8"),
        salt,
        opslimit=argon2id.OPSLIMIT_INTERACTIVE,
        memlimit=argon2id.MEMLIMIT_INTERACTIVE,
    )


def _get_salt() -> bytes:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    if SALT_FILE.is_file():
        return SALT_FILE.read_bytes()
    salt = nacl_random(argon2id.SALTBYTES)
    SALT_FILE.write_bytes(salt)
    return salt


def _load_vault() -> dict:
    if not VAULT_FILE.is_file():
        return {}
    try:
        return json.loads(VAULT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_vault(vault: dict):
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    VAULT_FILE.write_text(json.dumps(vault, indent=2), encoding="utf-8")


def encrypt_credential(name: str, value: str):
    _ensure_nacl()
    passphrase = _get_passphrase()
    salt = _get_salt()
    key = _derive_key(passphrase, salt)
    box = SecretBox(key)

    encrypted = box.encrypt(value.encode("utf-8"))

    vault = _load_vault()
    vault[name] = encrypted.hex()
    _save_vault(vault)
    print(f"Encrypted and stored: {name}")


def decrypt_credential(name: str) -> str:
    _ensure_nacl()
    passphrase = _get_passphrase()
    salt = _get_salt()
    key = _derive_key(passphrase, salt)
    box = SecretBox(key)

    vault = _load_vault()
    if name not in vault:
        print(f"Not found: {name}", file=sys.stderr)
        sys.exit(1)

    encrypted = bytes.fromhex(vault[name])
    decrypted = box.decrypt(encrypted).decode("utf-8")
    return decrypted


def list_credentials():
    vault = _load_vault()
    if not vault:
        print("Vault is empty")
        return
    for name in sorted(vault.keys()):
        print(f"  {name}")


def export_credentials():
    _ensure_nacl()
    passphrase = _get_passphrase()
    salt = _get_salt()
    key = _derive_key(passphrase, salt)
    box = SecretBox(key)

    vault = _load_vault()
    for name, encrypted_hex in sorted(vault.items()):
        encrypted = bytes.fromhex(encrypted_hex)
        value = box.decrypt(encrypted).decode("utf-8")
        print(f"export {name}='{value}'")


def main():
    parser = argparse.ArgumentParser(description="TeAka credential vault")
    sub = parser.add_subparsers(dest="command")

    enc = sub.add_parser("encrypt", help="Encrypt and store a credential")
    enc.add_argument("name", help="Credential name (e.g. KUCOIN_API_KEY)")
    enc.add_argument("value", help="Credential value")

    dec = sub.add_parser("decrypt", help="Decrypt and print a credential")
    dec.add_argument("name", help="Credential name")

    sub.add_parser("list", help="List stored credential names")
    sub.add_parser("export", help="Export all as shell env vars")

    args = parser.parse_args()

    if args.command == "encrypt":
        encrypt_credential(args.name, args.value)
    elif args.command == "decrypt":
        print(decrypt_credential(args.name))
    elif args.command == "list":
        list_credentials()
    elif args.command == "export":
        export_credentials()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
