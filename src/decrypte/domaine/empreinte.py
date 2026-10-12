import hashlib


def calculer_empreinte(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()