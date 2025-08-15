# sok/wallet.py (Phiên bản cuối cùng v12.6 - Final Fix)
# -*- coding: utf-8 -*-

from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature
from typing import Optional, Any
import hashlib
from .utils import hash_data 

def public_key_to_pem(public_key_obj: Any) -> str:
    return public_key_obj.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

def load_public_key_from_pem(pem_string: str):
    return serialization.load_pem_public_key(
        pem_string.encode('utf-8'),
        backend=default_backend()
    )

class Wallet:
    def __init__(self, private_key_pem: Optional[str] = None):
        if private_key_pem:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
        else:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        self.public_key = self.private_key.public_key()
        self.address = self.get_address()

    def get_address(self) -> str:
        public_key_pem = self.get_public_key_pem()
        return get_address_from_public_key_pem(public_key_pem)

    def get_private_key_pem(self) -> str:
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

    def get_public_key_pem(self) -> str:
        return public_key_to_pem(self.public_key)

def sign_data(private_key_obj: Any, data_hash: str) -> str:
    """Ký vào một chuỗi hash của GIAO DỊCH (dùng PSS padding)."""
    return private_key_obj.sign(
        bytes.fromhex(data_hash),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    ).hex()

def verify_signature(public_key_pem_string: str, signature_hex: str, original_message: str) -> bool:
    """
    Xác thực chữ ký của một TIN NHẮN GỐC.
    Hàm này sẽ tự động hash tin nhắn trước khi xác thực để khớp với client.
    """
    try:
        public_key = load_public_key_from_pem(public_key_pem_string)
        signature_bytes = bytes.fromhex(signature_hex)
        
        # 1. HASH LẠI TIN NHẮN GỐC - Đây là bước quan trọng để đồng bộ với client
        message_hash = hashlib.sha256(original_message.encode('utf-8')).digest()

        # 2. Thực hiện xác thực trên hash
        if isinstance(public_key, rsa.RSAPublicKey):
            # Dùng PKCS1v15 vì client cũng dùng nó để ký tin nhắn
            public_key.verify(
                signature_bytes,
                message_hash,
                padding.PKCS1v15(), 
                hashes.SHA256()
            )
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            # EC verify trực tiếp trên hash
            public_key.verify(
                signature_bytes,
                message_hash,
                ec.ECDSA(hashes.SHA256())
            )
        else:
            return False
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False

def get_address_from_public_key_pem(public_key_pem: str) -> str:
    """Tạo địa chỉ ví từ public key dạng PEM."""
    public_key_bytes = public_key_pem.encode('utf-8')
    raw_hash = hash_data(public_key_bytes)
    return f"SO{raw_hash}K"
