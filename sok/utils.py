# sok/utils.py
# -*- coding: utf-8 -*-

import hashlib
import json
import time
from typing import Any

def hash_data(data: Any) -> str:
    """Tạo mã băm SHA256 cho bất kỳ dữ liệu đầu vào nào."""
    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    if not isinstance(data, str):
        data_string = json.dumps(data, sort_keys=True)
    else:
        data_string = data
    return hashlib.sha256(data_string.encode()).hexdigest()

class Config:
    """Lớp chứa tất cả các hằng số cấu hình cho blockchain."""
    # Cấu hình Kinh tế & Khai thác
    DIFFICULTY = 5
    MINING_REWARD = 0.06
    HALVING_BLOCK_INTERVAL = 210000

    # Các mục tiêu kinh tế vĩ mô cho AI Agent
    TARGET_BLOCK_TIME_SECONDS = 50
    PENDING_TX_THRESHOLD = 100

    # Cấu hình Khối Genesis
    INITIAL_SUPPLY_TOKENS = 100000000
    FOUNDER_ADDRESS = "SOd94676cb061bd8e52cb4c89f4688d0962064e061c2a7900d53243a738e7959f5K"
    GENESIS_PREVIOUS_HASH = "0" * 64
    GENESIS_NONCE = 0

    # Cấu hình Mạng lưới
    DEFAULT_NODE_PORT = 5000
