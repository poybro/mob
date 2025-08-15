# -*- coding: utf-8 -*-
# backend.py (Thêm chức năng Import Wallet)

import os, sys, requests, json, time, logging, random, socket, threading, base64
from typing import List, Dict, Any, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

try:
    from sok.wallet import Wallet
except ImportError:
    print("LỖI: Không tìm thấy module 'sok.wallet'.")
    class Wallet:
        def __init__(self, private_key_pem=None): pass
        def get_private_key_pem(self): return "FAKE_PK"
        def get_public_key_pem(self): return "FAKE_PUB_KEY"
        def get_address(self): return "FAKE_ADDRESS"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

project_root = os.path.abspath(os.path.dirname(__file__))
DEFAULT_WALLET_FILE = "my_smart_wallet.enc"

class BackendLogic:
    # --- Toàn bộ các hàm __init__ và các hàm khác giữ nguyên ---
    def __init__(self, app_data_dir: str, log_callback=None):
        self.app_data_dir = app_data_dir
        try:
            os.makedirs(self.app_data_dir, exist_ok=True)
        except Exception as e:
            logging.error(f"KHÔNG THỂ TẠO THƯ MỤC DỮ LIỆU! Lỗi: {e}", exc_info=True)
            
        self.wallet_file_path = os.path.join(self.app_data_dir, DEFAULT_WALLET_FILE)
        
        self.wallet: Optional[Wallet] = None
        self.server_url: Optional[str] = None
        self.treasury_address: Optional[str] = None
        self.price_info: Dict[str, Any] = {}
        
        self.miner_status = {"state": "STOPPED", "current_node": "None", "last_log": "Thợ mỏ chưa được khởi động."}
        self.miner_is_active = threading.Event()
        self.miner_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.log_callback = log_callback or (lambda state, msg: logging.info(f"Log callback: [{state}] {msg}"))

    # --- Các hàm mã hóa (_derive_key, _encrypt_pem, _decrypt_pem) giữ nguyên ---
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
        return base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))

    def _encrypt_pem(self, pem_data: str, password: str) -> bytes:
        salt = os.urandom(16); key = self._derive_key(password, salt)
        return salt + Fernet(key).encrypt(pem_data.encode('utf-8'))

    def _decrypt_pem(self, encrypted_data: bytes, password: str) -> Optional[str]:
        try:
            salt, token = encrypted_data[:16], encrypted_data[16:]
            key = self._derive_key(password, salt)
            return Fernet(key).decrypt(token).decode('utf-8')
        except (InvalidToken, IndexError, TypeError): return None

    # --- Các hàm quản lý ví (load, create) giữ nguyên ---
    def does_wallet_exist(self) -> bool:
        return os.path.exists(self.wallet_file_path)

    def load_wallet_from_file(self, password: str) -> (bool, str):
        if not self.does_wallet_exist(): 
            return False, "File ví không tồn tại."
        with open(self.wallet_file_path, 'rb') as f: 
            pem_data = self._decrypt_pem(f.read(), password)
        if pem_data:
            self.wallet = Wallet(private_key_pem=pem_data)
            return True, "Giải mã và tải ví thành công."
        else: 
            return False, "Mật khẩu sai hoặc file ví bị lỗi."

    def create_new_wallet(self, password: str) -> (bool, str):
        try:
            self.wallet = Wallet()
            pem_data = self.wallet.get_private_key_pem()
            encrypted_data = self._encrypt_pem(pem_data, password)
            with open(self.wallet_file_path, 'wb') as f: 
                f.write(encrypted_data)
            return True, pem_data
        except Exception as e:
            return False, f"Lỗi không xác định khi tạo ví: {e}"

    # --- [HÀM MỚI] ---
    def import_wallet_from_pem(self, pem_data: str, password: str) -> (bool, str):
        """Nhập ví từ Private Key PEM và mã hóa với mật khẩu mới."""
        try:
            # 1. Thử tạo đối tượng Wallet để xác thực key hợp lệ
            temp_wallet = Wallet(private_key_pem=pem_data)
            
            # 2. Mã hóa key với mật khẩu mới
            encrypted_data = self._encrypt_pem(pem_data, password)
            
            # 3. Lưu vào file
            with open(self.wallet_file_path, 'wb') as f: 
                f.write(encrypted_data)
                
            # 4. Gán ví hiện tại
            self.wallet = temp_wallet
            return True, "Nhập và mã hóa ví thành công."
        except ValueError:
            return False, "Private Key không hợp lệ hoặc bị lỗi định dạng."
        except Exception as e:
            return False, f"Lỗi khi nhập ví: {e}"

    # --- [HÀM MỚI] ---
    def get_private_key_for_backup(self) -> Optional[str]:
        """Lấy private key từ ví đã được tải."""
        if self.wallet:
            return self.wallet.get_private_key_pem()
        return None

    # --- Toàn bộ các hàm còn lại (connect_to_server, _make_api_request, v.v...) giữ nguyên ---
    def connect_to_server(self, server_ip: str) -> (bool, str):
        self.server_url = f"http://{server_ip}:9000"
        try:
            response = requests.get(f"{self.server_url}/ping", timeout=5)
            if response.status_code == 200:
                payment_data = self._make_api_request('GET', '/api/v1/payment_info')
                if payment_data and 'error' not in payment_data:
                    self.treasury_address = payment_data.get('treasury_address')
                    self.price_info = payment_data
                    return True, "Kết nối và tải cấu hình thành công."
                return False, f"Kết nối được nhưng không thể tải cấu hình: {payment_data.get('error', 'Lỗi không rõ') if payment_data else 'Không có phản hồi'}"
            return False, f"Server phản hồi lỗi: {response.status_code}"
        except requests.RequestException as e:
            return False, f"Không thể kết nối đến server: {e}"
            
    def _make_api_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        if not self.server_url: 
            logging.error("Lỗi gọi API: server_url chưa được thiết lập.")
            return {"error": "URL của server chưa được thiết lập."}
        url = f"{self.server_url}{endpoint}"
        kwargs.setdefault('timeout', 15)
        try:
            response = requests.request(method.upper(), url, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            logging.error(f"Lỗi HTTP khi gọi {url}: {e.response.status_code} - {e.response.text}")
            return {"error": f"Lỗi từ server: {e.response.status_code}", "details": e.response.text}
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            logging.error(f"Lỗi gọi API đến {url}: {e}")
            return {"error": f"Không thể hoàn thành yêu cầu: {e}"}
    
    def refresh_dashboard(self) -> Optional[Dict]:
        if not self.wallet: return None
        profile_data = self._make_api_request('GET', f"/api/v1/user_profile/{self.wallet.get_address()}")
        stats_data = self._make_api_request('GET', '/api/v1/dashboard_stats')
        return {"profile": profile_data or {}, "stats": stats_data or {}}
        
    def send_transaction(self, recipient: str, amount_str: str) -> Optional[Dict]:
        if not self.wallet: return {"error": "Ví chưa được mở khóa."}
        return self._make_api_request('POST', '/api/direct_fund', json={
            "private_key_pem": self.wallet.get_private_key_pem(), 
            "recipient_address": recipient, 
            "amount": amount_str
        })

    def get_transaction_history(self) -> Optional[List[Dict]]:
        if not self.wallet: return None
        return self._make_api_request('GET', f"/api/v1/transaction_history/{self.wallet.get_address()}")

    def add_website(self, url: str) -> Optional[Dict]:
        if not self.wallet: return {"error": "Ví chưa được mở khóa."}
        return self._make_api_request('POST', '/api/v1/websites/add', json={
            "url": url, "owner_pk_pem": self.wallet.get_public_key_pem()
        })

    def remove_website(self, url: str) -> Optional[Dict]:
        if not self.wallet: return {"error": "Ví chưa được mở khóa."}
        return self._make_api_request('POST', '/api/v1/websites/remove', json={
            "url": url, "owner_address": self.wallet.get_address()
        })

    def list_my_websites(self) -> Optional[List[Dict]]:
        if not self.wallet: return None
        return self._make_api_request('GET', f"/api/v1/websites/list?owner={self.wallet.get_address()}")
    
    def get_miner_status(self):
        return self.miner_status
        
    def start_miner(self):
        if not self.miner_is_active.is_set():
            self.miner_is_active.set()
            if not self.miner_thread or not self.miner_thread.is_alive():
                self.stop_event.clear()
                self.miner_thread = threading.Thread(target=self._miner_main_loop, daemon=True, name="MinerThread")
                self.miner_thread.start()
            if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
                self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="HeartbeatThread")
                self.heartbeat_thread.start()
            self._miner_log("STARTING", "Đã gửi lệnh kích hoạt thợ mỏ.")
            return True, "Thợ mỏ đã được kích hoạt."
        return False, "Thợ mỏ đã đang chạy."

    def stop_miner(self):
        if self.miner_is_active.is_set():
            self.miner_is_active.clear()
            self._miner_log("PAUSED", "Đã nhận lệnh tạm dừng từ người dùng.")
            return True, "Đã gửi lệnh tạm dừng."
        return False, "Thợ mỏ đã dừng từ trước."

    def shutdown(self):
        self.stop_event.set()
        
    def _miner_log(self, state: str, message: str):
        self.miner_status.update({"state": state, "last_log": message})
        self.log_callback(state, message)
        
    def _miner_load_all_known_nodes(self) -> List[str]:
        nodes = set()
        for file in ["live_network_nodes.json", "bootstrap_config.json"]:
            config_path = os.path.join(project_root, file)
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f: data = json.load(f)
                    if "active_nodes" in data: nodes.update(data["active_nodes"])
                    if "trusted_bootstrap_peers" in data: nodes.update([p.get('last_known_address') for p in data["trusted_bootstrap_peers"].values()])
                except Exception: pass
        return list(filter(None, nodes))

    def _miner_find_best_node(self) -> Optional[Dict]:
        known_nodes = self._miner_load_all_known_nodes()
        if not known_nodes: self._miner_log("FAILED", "Không có node nào trong file config."); return None
        healthy_nodes = []
        threads = []
        def check_node(url, result_list):
            try:
                stats = requests.get(f'{url}/chain/stats', timeout=4).json()
                result_list.append({"url": url, "height": stats.get('block_height', -1)})
            except: pass
        for url in known_nodes:
            thread = threading.Thread(target=check_node, args=(url, healthy_nodes)); threads.append(thread); thread.start()
        for thread in threads: thread.join(4)
        if not healthy_nodes: self._miner_log("FAILED", "Không tìm thấy node nào hoạt động."); return None
        max_height = max(n['height'] for n in healthy_nodes)
        top_tier = [n for n in healthy_nodes if n['height'] >= max_height - 1]
        return random.choice(top_tier) if top_tier else None
        
    def _miner_main_loop(self):
        last_node_re_evaluation_time = 0
        while not self.stop_event.is_set():
            if not self.miner_is_active.is_set():
                if self.miner_status['state'] not in ["PAUSED", "STOPPED"]: self._miner_log("PAUSED", "Chờ lệnh...")
                self.stop_event.wait(5)
                continue
            try:
                node_is_stale = (time.time() - last_node_re_evaluation_time) > 300
                if not self.miner_status.get('current_node') or node_is_stale:
                    self._miner_log("SEARCHING", "Bắt đầu quét mạng lưới...")
                    target_node_info = self._miner_find_best_node()
                    if not target_node_info:
                        self._miner_log("FAILED", f"Không tìm thấy node. Thử lại sau 30s.")
                        self.stop_event.wait(30)
                        continue
                    self.miner_status['current_node'] = target_node_info['url']
                    last_node_re_evaluation_time = time.time()
                    self._miner_log("NODE_SWITCHED", f"Đã chọn: {self.miner_status['current_node']} (Block: {target_node_info.get('height')})")
                node_url = self.miner_status['current_node']
                self._miner_log("MINING", f"Gửi yêu cầu khai thác...")
                response = requests.get(f"{node_url}/mine", params={'miner_address': self.wallet.get_address()}, timeout=130)
                if response.status_code == 200:
                    self._miner_log("SUCCESS", f"Đã đào Khối #{response.json().get('block', {}).get('index', '?')}.")
                    self.stop_event.wait(120)
                elif response.status_code == 409:
                    pause_duration = random.uniform(3, 8)
                    self._miner_log("CONFLICT", f"Cạnh tranh! Tạm dừng {pause_duration:.1f}s.")
                    self.miner_status['current_node'] = None; self.stop_event.wait(pause_duration)
                else:
                    self._miner_log("FAILED", f"Node từ chối: {response.status_code}")
                    self.miner_status['current_node'] = None; self.stop_event.wait(5)
            except requests.exceptions.ReadTimeout:
                pause_duration = random.uniform(3, 8)
                self._miner_log("TIMEOUT", f"Hết thời gian chờ. Tạm dừng {pause_duration:.1f}s.")
                self.miner_status['current_node'] = None; self.stop_event.wait(pause_duration)
            except requests.exceptions.RequestException:
                self._miner_log("CONNECTION_ERROR", f"Mất kết nối tới node.")
                self.miner_status['current_node'] = None; self.stop_event.wait(5)
            except Exception as e:
                self._miner_log("CRITICAL", f"Lỗi nghiêm trọng: {e}")
                self.miner_status['current_node'] = None; self.stop_event.wait(60)

    def _heartbeat_loop(self):
        while not self.stop_event.is_set():
            self.stop_event.wait(90)
            if self.miner_is_active.is_set() and self.wallet:
                try: requests.post(f"{self.server_url}/heartbeat", json={"worker_address": self.wallet.get_address(), "type": "miner", "status": self.miner_status['state']}, timeout=5)
                except: pass
