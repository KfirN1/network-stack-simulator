import socket
import time
import json
import os
from Shared.config import *

DB_FILE = DHCP_DB_PATH

active_leases = {}
available_ips = []

def load_db():
    # Loading the database from disk and restoring the free buffer
    global active_leases, available_ips
    full_pool = [f"{DHCP_BASE_IP}{i}" for i in range(DHCP_POOL_START, DHCP_POOL_END + 1)]
    
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                active_leases = json.load(f)
            print(f"[DHCP Server] Database loaded. {len(active_leases)} leases recovered.")
        except: active_leases = {}
    
    taken_ips = [data["ip"] for data in active_leases.values()]
    available_ips = [ip for ip in full_pool if ip not in taken_ips]

def save_db():
    # Save current borrowing status to disk
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, "w") as f:
            json.dump(active_leases, f, indent=4)
    except: pass

def clean_expired_leases():
    # Scan and clean up expired addresses
    current_time = time.time()
    expired_ids = [cid for cid, data in active_leases.items()
                   if current_time - data["timestamp"] > DHCP_LEASE_TIME]
    
    if expired_ids:
        for cid in expired_ids:
            ip_to_return = active_leases[cid]["ip"]
            available_ips.append(ip_to_return)
            del active_leases[cid]
        save_db()

def get_ip_for_client(client_id):
    clean_expired_leases()
    if client_id in active_leases:
        active_leases[client_id]["timestamp"] = time.time()
        save_db()
        return active_leases[client_id]["ip"]
    
    if available_ips:
        new_ip = available_ips.pop(0)
        active_leases[client_id] = {"ip": new_ip, "timestamp": time.time()}
        save_db()
        return new_ip
    return None

def start_dhcp_server():
    print("--- Stateful DHCP Server Online ---")
    load_db()
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((LOCALHOST, DHCP_SERVER_PORT))
        print(f"[DHCP Server] Listening on {DHCP_SERVER_PORT}...")

        while True:
            try:
                data, addr = server_sock.recvfrom(MAX_BUFFER_SIZE)
                parts = data.decode().split("|")
                m_type, client_id = parts[0], parts[1] if len(parts) > 1 else "Unknown"

                if m_type == DHCP_DISCOVER:
                    ip = get_ip_for_client(client_id)
                    if ip:
                        server_sock.sendto(f"{DHCP_OFFER}:{ip}".encode(), addr)

                elif m_type == DHCP_REQUEST:
                    if client_id in active_leases:
                        ip = active_leases[client_id]["ip"]
                        active_leases[client_id]["timestamp"] = time.time()
                        save_db()
                        resp = f"{DHCP_ACK}|IP:{ip}|Mask:{DHCP_SUBNET_MASK}|GW:{DHCP_GATEWAY}|DNS:{DNS_SERVER_IP}|Lease_time:{DHCP_LEASE_TIME}"
                        server_sock.sendto(resp.encode(), addr)

                elif m_type == "DHCP_RELEASE":
                    if client_id in active_leases:
                        available_ips.append(active_leases[client_id]["ip"])
                        del active_leases[client_id]
                        save_db()
                        print(f"[DHCP Server] Released IP for {client_id}")

            except Exception: pass

if __name__ == "__main__":
    start_dhcp_server()