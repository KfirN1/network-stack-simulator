import socket
import random
from Shared.config import *

def resolve_dns(domain_name, assigned_ip): 
    print(f"[DNS Client] Resolving domain: {domain_name} (Identity: {assigned_ip})")
    query_id = str(random.randint(1000, 9999))

    print(f"[DNS Client] Querying {domain_name} (ID: {query_id}) via DoH...")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(DNS_TIMEOUT)
            sock.connect((LOCALHOST, DNS_HTTP_PORT))

            request = (f"GET /resolve?name={domain_name}&id={query_id} HTTP/1.1\r\n"
                       f"Host: {LOCALHOST}\r\n"
                       f"X-Assigned-IP: {assigned_ip}\r\n" 
                       f"\r\n")
            
            sock.sendall(request.encode())
            
            data = sock.recv(MAX_BUFFER_SIZE).decode()

            if "\r\n\r\n" in data:
                response_body = data.split("\r\n\r\n")[1]
                parts = response_body.split("|")

                if len(parts) >= 2:
                    resp_id, ip = parts[0], parts[1]

                    if resp_id == query_id and ip != "NOT FOUND":
                        print(f"[DNS Client] Resolved via DoH: {ip}")
                        return ip
                    
    except Exception as e:
        print(f"[DNS Client] DoH failed or timeout: {e}")

    print(f"[DNS Client] Querying {domain_name} (ID: {query_id}) via UDP...")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(DNS_TIMEOUT)
        
        dns_payload = f"{query_id}|{domain_name}|SRC_IP:{assigned_ip}"
        sock.sendto(dns_payload.encode(), (LOCALHOST, DNS_PORT))

        try:
            data, _ = sock.recvfrom(MAX_BUFFER_SIZE)
            parts = data.decode().split("|")
            
            if len(parts) >= 2:
                resp_id = parts[0]
                ip = parts[1]

                if resp_id == query_id and ip != "NOT FOUND":
                    ttl = parts[3] if len(parts) > 3 else "N/A"
                    print(f"[DNS Client] Resolved via UDP: {ip} (TTL: {ttl})")
                    return ip
                
        except socket.timeout:
            print("[DNS Client] DNS UDP Timeout.")
    
    return None