import hashlib
import os
import re
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet

def canonicalize_identifier(raw_str: str) -> str:
    """Strips outer whitespace and lowercases string for deterministic matching."""
    if not raw_str:
        return ""
    return raw_str.strip().lower()

def hash_identity_sha256(identifier: str, salt: str = "") -> str:
    """
    Computes a canonicalized deterministic SHA-256 hash.
    Note: Deterministic hashing permits identity joining across systems,
    but unsalted hashes of small-cardinality values are susceptible to dictionary attacks.
    """
    canonical = canonicalize_identifier(identifier)
    payload = f"{salt}{canonical}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def get_or_create_encryption_key(key_file_path: Optional[Path] = None) -> bytes:
    """Retrieves encryption key from environment variable or generates/loads a secure keyfile."""
    env_key = os.getenv("DATA_ENCRYPTION_KEY")
    if env_key:
        return env_key.encode("utf-8")

    if key_file_path:
        key_file_path = Path(key_file_path)
        if key_file_path.exists():
            return key_file_path.read_bytes().strip()
        key = Fernet.generate_key()
        key_file_path.parent.mkdir(parents=True, exist_ok=True)
        key_file_path.write_bytes(key)
        return key

    return Fernet.generate_key()

def encrypt_column_value(plaintext: str, key: bytes) -> str:
    """Encrypts sensitive column string using Fernet authenticated encryption."""
    if plaintext is None:
        return ""
    f = Fernet(key)
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_column_value(ciphertext: str, key: bytes) -> str:
    """Decrypts ciphertext back into plaintext."""
    if not ciphertext:
        return ""
    f = Fernet(key)
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

def mask_email(email: str) -> str:
    """
    Masks email for analyst view (e.g., 'alice.smith@example.com' -> 'a***h@example.com').
    """
    if not email or "@" not in email:
        return "***@masked.domain"
    user_part, domain_part = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = user_part[0] + "***" + user_part[-1]
    return f"{masked_user}@{domain_part}"

def mask_name(full_name: str) -> str:
    """Masks name components (e.g. 'Alice Johnson' -> 'A**** J******')."""
    if not full_name:
        return "Anonymous"
    parts = full_name.strip().split()
    masked_parts = []
    for p in parts:
        if len(p) <= 1:
            masked_parts.append(p)
        else:
            masked_parts.append(p[0] + ("*" * (len(p) - 1)))
    return " ".join(masked_parts)
