# sok/node_api.py
# -*- coding: utf-8 -*-

import os
import json
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from .transaction import Transaction
from .wallet import Wallet
from .blockchain import Block

logger = logging.getLogger(__name__)

# --- CÁC HÀM TRỢ GIÚP ĐỂ CẬP NHẬT FILE CỤC BỘ ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIVE_NETWORK_CONFIG_FILE = os.path.join(project_root, 'live_network_nodes.json')

def update_local_map_file(nodes_list: list):
    try:
        sorted_nodes = sorted(list(set(nodes_list)))
        temp_file = LIVE_NETWORK_CONFIG_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump({"active_nodes": sorted_nodes}, f, indent=2)
        os.replace(temp_file, LIVE_NETWORK_CONFIG_FILE)
        logger.info(f"[API] Đã cập nhật thành công tệp bản đồ mạng cục bộ '{os.path.basename(LIVE_NETWORK_CONFIG_FILE)}'")
    except Exception as e:
        logger.error(f"[API] Lỗi khi ghi tệp bản đồ mạng cục bộ: {e}")

def create_app(blockchain, p2p_manager, node_wallet: Wallet, genesis_wallet: Wallet = None):
    app = Flask(__name__)
    CORS(app)
    
    # === API ĐỂ LAN TRUYỀN BẢN ĐỒ MẠNG ===
    @app.route('/nodes/update_map', methods=['POST'])
    def update_network_map():
        data = request.get_json()
        if not data or 'active_nodes' not in data:
            return jsonify({'error': 'Dữ liệu không hợp lệ.'}), 400
        nodes_list = data['active_nodes']
        update_thread = threading.Thread(target=update_local_map_file, args=(nodes_list,))
        update_thread.start()
        return jsonify({'message': 'Đã nhận bản đồ.'}), 202

    # --- ENDPOINTS CHÍNH ---
    
    @app.route('/genesis/info', methods=['GET'])
    def get_genesis_info():
        if not genesis_wallet: return jsonify({'error': 'Forbidden.'}), 403
        return jsonify({ 'genesis_address': genesis_wallet.get_address(), 'current_balance': blockchain.get_balance(genesis_wallet.get_address()) }), 200
        
    @app.route('/handshake', methods=['GET'])
    def handshake():
        return jsonify({"node_id": node_wallet.get_address()}), 200

    @app.route('/nodes/peers', methods=['GET'])
    def get_peers():
        with blockchain.peer_lock:
            return jsonify(blockchain.peers), 200

    @app.route('/mine', methods=['GET'])
    def mine():
        miner_address = request.args.get('miner_address')
        if not miner_address: return jsonify({'error': 'Yêu cầu địa chỉ của thợ mỏ.'}), 400
        new_block = blockchain.mine_pending_transactions(miner_address)
        p2p_manager.broadcast_block(new_block)
        return jsonify({'message': 'Đã khai thác khối mới!', 'block': new_block.to_dict()}), 200

    @app.route('/transactions/new', methods=['POST'])
    def new_transaction():
        values = request.get_json()
        if not all(k in values for k in ['sender_public_key_pem', 'recipient_address', 'amount', 'signature']): 
            return jsonify({'error': 'Thiếu trường dữ liệu.'}), 400
        
        tx = Transaction.from_dict(values)
        
        # SỬA LỖI: Xử lý đúng tuple (is_valid, message) trả về từ hàm is_valid
        is_valid, message = tx.is_valid(blockchain)
        if not is_valid: 
            logger.warning(f"Từ chối giao dịch không hợp lệ: {message}")
            return jsonify({'error': f'Giao dịch không hợp lệ: {message}'}), 400

        if blockchain.add_transaction(values):
            p2p_manager.broadcast_transaction(values)
            return jsonify({'message': 'Giao dịch sẽ được thêm vào khối tiếp theo.'}), 201
        
        return jsonify({'message': 'Giao dịch đã tồn tại hoặc đã được xử lý.'}), 400

    @app.route('/mempool', methods=['GET'])
    def get_mempool():
        """
        API endpoint mới để trả về thông tin về các giao dịch đang chờ (mempool).
        Discovery Agent và Intelligent Miner sẽ gọi API này.
        """
        pending_txs = blockchain.pending_transactions
        response = {
            'pending_transactions': pending_txs,
            'count': len(pending_txs)
        }
        return jsonify(response), 200

    @app.route('/chain', methods=['GET'])
    def get_chain():
        # SỬA LỖI: Thêm logic để xử lý tham số `start`
        start_index_str = request.args.get('start')
        full_chain_data = blockchain.get_full_chain_for_api()

        if start_index_str:
            try:
                start_index = int(start_index_str)
                filtered_chain = [block for block in full_chain_data if block['index'] >= start_index]
                return jsonify({'chain': filtered_chain, 'length': len(full_chain_data)}), 200
            except ValueError:
                return jsonify({'error': 'Tham số start phải là một số nguyên.'}), 400
        
        return jsonify({'chain': full_chain_data, 'length': len(full_chain_data)}), 200

    @app.route('/balance/<address>', methods=['GET'])
    def get_balance(address):
        if not address: return jsonify({'error': 'Địa chỉ không được để trống.'}), 400
        return jsonify({'address': address, 'balance': blockchain.get_balance(address)}), 200

    @app.route('/chain/stats', methods=['GET'])
    def get_chain_stats():
        try:
            stats = {
                "total_supply": blockchain.calculate_actual_total_supply(), 
                "block_height": blockchain.last_block.index, 
                "pending_tx_count": len(blockchain.pending_transactions), 
                "difficulty": blockchain.difficulty,
                "peer_count": len(blockchain.peers)
            }
            return jsonify(stats), 200
        except Exception as e:
            logger.error(f"Lỗi khi lấy thống kê chuỗi: {e}")
            return jsonify({"error": "Không thể xử lý yêu cầu thống kê."}), 500

    # Các endpoint P2P để nhận dữ liệu từ các node khác
    @app.route('/blocks/add_from_peer', methods=['POST'])
    def add_block_from_peer_api():
        block_data = request.get_json()
        if not block_data:
            return "Dữ liệu không hợp lệ.", 400
        if blockchain.add_block_from_peer(block_data):
            return "Đã chấp nhận khối.", 200
        return "Xung đột hoặc khối không hợp lệ.", 409

    @app.route('/transactions/add_from_peer', methods=['POST'])
    def add_transaction_from_peer():
        tx_data = request.get_json()
        if not tx_data:
            return "Dữ liệu không hợp lệ.", 400
        if blockchain.add_transaction(tx_data):
            return "Đã chấp nhận giao dịch.", 200
        return "Giao dịch đã tồn tại.", 409
            
    return app
