import hashlib
import secrets


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    candidate = hash_api_key(raw_key)
    return secrets.compare_digest(candidate, stored_hash)
