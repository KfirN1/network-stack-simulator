import socket
import threading
import time
import requests
import urllib.parse
import json
import os
from Shared.config import *

DNS_DB_FILE = DNS_DB_PATH

DOH_PROVIDERS = [
    "https://dns.google/resolve",
    "https://cloudflare-dns.com/dns-query"
]

http_session = requests.Session()
http_session.headers.update({"Accept": "application/dns-json"})

DNS_resolver_cache = {}

def load_dns_cache():
    # Loading the cache and integrating local persistent records
    global DNS_resolver_cache
    
    default_records = {
        (APP_SERVER_NAME.lower(), "A"): {
            "value": APP_SERVER_IP, "ttl": 3600, "timestamp": time.time()
        },
        ("alias-server.com", "CNAME"): {
            "value": APP_SERVER_NAME, "ttl": 3600, "timestamp": time.time()
        }
    }

    if os.path.exists(DNS_DB_FILE):
        try:
            with open(DNS_DB_FILE, "r") as f:
                loaded = json.load(f)
                current_time = time.time()
                for key_str, data in loaded.items():
                    domain, qtype = key_str.split("|")
                    if current_time - data["timestamp"] < data["ttl"]:
                        DNS_resolver_cache[(domain, qtype)] = data
            print(f"[DNS Server] Advanced cache loaded from disk.")
        except Exception as e:
            print(f"[DNS Server] Error loading DB: {e}")
    
    DNS_resolver_cache.update(default_records)
    save_dns_cache()

def save_dns_cache():
    # Save current state to disk
    try:
        to_save = {f"{k[0]}|{k[1]}": v for k, v in DNS_resolver_cache.items() 
                   if k[0] != APP_SERVER_NAME.lower()}
        
        os.makedirs(os.path.dirname(DNS_DB_FILE), exist_ok=True)
        
        with open(DNS_DB_FILE, "w") as f:
            json.dump(to_save, f, indent=4)
        print(f"[DNS Server] Database updated at: {DNS_DB_FILE}")
    except Exception as e:
        print(f"[DNS Server] Save error: {e}")

def fetch_external_dns(domain, qtype="A"):
    domain = domain.lower().strip()
    if domain == APP_SERVER_NAME.lower():
        return DNS_resolver_cache.get((domain, "A"))

    for provider_url in DOH_PROVIDERS:
        try:
            params = {"name": domain, "type": qtype}
            response = http_session.get(provider_url, params=params, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if "Answer" in data:
                    answer = data["Answer"][0]
                    record = {
                        "value": answer["data"],
                        "type": qtype,
                        "ttl": answer["TTL"],
                        "timestamp": time.time()
                    }
                    DNS_resolver_cache[(domain, qtype)] = record
                    save_dns_cache()
                    return record
        except Exception: continue
    return None

def get_record(domain, qtype="A"):
    domain = domain.lower().strip()
    qtype = qtype.upper().strip()
    record = DNS_resolver_cache.get((domain, qtype))
    if record and (time.time() - record["timestamp"] < record["ttl"]):
        return record
    return fetch_external_dns(domain, qtype)

def handle_udp_query():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((LOCALHOST, DNS_PORT))
        print(f"[DNS UDP] Listening on {DNS_PORT}...")
        while True:
            try:
                data, addr = server_sock.recvfrom(MAX_BUFFER_SIZE)
                parts = data.decode().split("|")
                if len(parts) < 2: continue
                query_id, domain = parts[0], parts[1]
                qtype = parts[2] if len(parts) > 2 else "A"
                record = get_record(domain, qtype)
                resp = f"{query_id}|{record['value']}|{qtype}|{int(record['ttl'])}" if record else f"{query_id}|NOT FOUND"
                server_sock.sendto(resp.encode(), addr)
            except Exception: pass

def handle_http_query():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((LOCALHOST, DNS_HTTP_PORT))
        server_sock.listen(10)
        print(f"[DNS DoH Local] Listening on {DNS_HTTP_PORT}...")
        while True:
            client_sock, _ = server_sock.accept()
            with client_sock:
                try:
                    data = client_sock.recv(MAX_BUFFER_SIZE).decode()
                    if "GET" in data:
                        path = data.split(' ')[1]
                        params = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
                        domain = params.get('name', [None])[0]
                        qtype = params.get('type', ["A"])[0]
                        query_id = params.get('id', ["0"])[0]
                        record = get_record(domain, qtype) if domain else None
                        val = record['value'] if record else "NOT FOUND"
                        resp_body = f"{query_id}|{val}"
                        http_response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(resp_body)}\r\n\r\n{resp_body}"
                        client_sock.sendall(http_response.encode())
                except Exception: pass

def start_dns_server():
    print("\n--- Advanced Stateful DNS Server Online ---")
    load_dns_cache()
    threading.Thread(target=handle_udp_query, daemon=True).start()
    threading.Thread(target=handle_http_query, daemon=True).start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    start_dns_server()