# sok/transaction.py (Phiên bản cuối cùng v12.6 - Final Fix)
import json, time, logging, hashlib
from typing import Optional, TYPE_CHECKING
from . import wallet
from .utils import hash_data

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.backends import default_backend

if TYPE_CHECKING:
    from .blockchain import Blockchain 

class Transaction:
    def __init__(self, sender_public_key_pem: str, recipient_address: str, amount: float, timestamp: Optional[float] = None, signature: Optional[str] = None, sender_address: Optional[str] = None):
        self.sender_public_key_pem = sender_public_key_pem; self.recipient_address = recipient_address; self.amount = float(amount)
        self.timestamp = timestamp or time.time(); self.signature = signature
        self.sender_address = sender_address or ("0" if sender_public_key_pem == "0" else wallet.get_address_from_public_key_pem(sender_public_key_pem))
    
    def get_signing_data(self) -> dict:
        return {'sender_public_key_pem': self.sender_public_key_pem, 'recipient_address': self.recipient_address, 'amount': self.amount, 'timestamp': self.timestamp}
    
    def to_dict(self) -> dict:
        data = self.get_signing_data(); data['sender_address'] = self.sender_address; data['signature'] = self.signature
        return data
        
    def calculate_hash(self) -> str:
        return hash_data(json.dumps(self.get_signing_data(), sort_keys=True).encode('utf-8'))
        
    def sign(self, private_key_obj):
        if not self.signature: self.signature = wallet.sign_data(private_key_obj, self.calculate_hash())
        
    def is_valid(self, blockchain_instance: 'Blockchain') -> tuple[bool, str]:
        # Hàm này dùng để xác thực GIAO DỊCH, sử dụng padding PSS
        def verify_transaction_signature(public_key_pem_string: str, data_hash: str, signature_hex: str) -> bool:
            try:
                public_key_loaded = wallet.load_public_key_from_pem(public_key_pem_string)
                public_key_loaded.verify(
                    bytes.fromhex(signature_hex),
                    bytes.fromhex(data_hash),
                    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                    hashes.SHA256()
                )
                return True
            except Exception: return False

        if self.sender_public_key_pem == "0": return (True, "Giao dịch hệ thống hợp lệ") if self.signature in ["genesis_transaction", "mining_reward"] else (False, "Giao dịch hệ thống không hợp lệ")
        if not all([self.sender_public_key_pem, self.recipient_address, self.signature, self.amount is not None]): return False, "Thiếu trường dữ liệu quan trọng"
        if wallet.get_address_from_public_key_pem(self.sender_public_key_pem) != self.sender_address: return False, "Địa chỉ người gửi không khớp với khóa công khai."
        if not verify_transaction_signature(self.sender_public_key_pem, self.calculate_hash(), self.signature): return False, f"Chữ ký giao dịch không hợp lệ cho địa chỉ {self.sender_address[:10]}..."
        if blockchain_instance.get_balance(self.sender_address) < self.amount: return False, f"Số dư không đủ. {self.sender_address[:10]}... chỉ có {blockchain_instance.get_balance(self.sender_address)} SOK."
        if self.amount <= 0: return False, "Số tiền giao dịch phải lớn hơn 0."
        return True, "Giao dịch hợp lệ"

    @staticmethod
    def from_dict(data: dict):
        required_keys = ['sender_public_key_pem', 'recipient_address', 'amount']
        if not all(k in data for k in required_keys): raise ValueError("Thiếu các trường dữ liệu bắt buộc.")
        return Transaction(data['sender_public_key_pem'], data['recipient_address'], data['amount'], data.get('timestamp'), data.get('signature'), data.get('sender_address'))
    
    @staticmethod
    def sign_message(private_key_pem: str, message: str) -> str:
        """Ký một TIN NHẮN bất kỳ (dùng PKCS1v15 padding)."""
        try:
            private_key = serialization.load_pem_private_key(private_key_pem.encode('utf-8'), password=None, backend=default_backend())
            
            # 1. HASH tin nhắn trước khi ký.
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()
            
            if isinstance(private_key, rsa.RSAPrivateKey):
                signature_bytes = private_key.sign(
                    message_hash,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            elif isinstance(private_key, ec.EllipticCurvePrivateKey):
                signature_bytes = private_key.sign(
                    message_hash,
                    ec.ECDSA(hashes.SHA256())
                )
            else: raise TypeError(f"Loại khóa không được hỗ trợ: {type(private_key)}")
            return signature_bytes.hex()
        except Exception as e:
            logging.error(f"Lỗi khi tạo chữ ký cho tin nhắn: {e}", exc_info=True); raise
