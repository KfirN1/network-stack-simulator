import socket
import os
from Shared.config import *
from Shared.utils import fetch_external_content, sanitize_cache_name

def build_http_response(status_code, status_text, content_type, body):
    response_header = (f"HTTP/1.1 {status_code} {status_text}\r\n"
                       f"Content-Type: {content_type}\r\n"
                       f"Content-Length: {len(body)}\r\n"
                       f"Access-Control-Allow-Origin: *\r\n" 
                       f"Connection: keep-alive\r\n\r\n")
    return response_header.encode() + body

def handle_tcp_client(client_sock, addr):
    client_sock.settimeout(10.0)
    try:
        data = client_sock.recv(MAX_BUFFER_SIZE).decode(errors='ignore')

        if not data:
            return

        assigned_ip = "Unknown (No DHCP identity)"
        for line in data.split('\r\n'):
            if line.startswith("X-Assigned-IP:"):
                assigned_ip = line.split(":")[1].strip()

        print(f"[App Server TCP] Connection from {addr} | Identity (Assigned IP): {assigned_ip}")

        parts = data.split('\n')[0].split(' ')

        if len(parts) < 2:
            return
        
        requested_uri = parts[1].lstrip('/')

        if requested_uri in ["", "/"]:
            requested_uri = "index.html"

        file_path = os.path.join(FILES_DIRECTORY, requested_uri)
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            print(f"[App Server] Cache Hit! Serving local copy: {requested_uri}")
            with open(file_path, "rb") as f:
                content = f.read()

            ctype = "text/html" if requested_uri.endswith(".html") else "application/octet-stream"
            response = build_http_response(200, "OK", ctype, content)
        
        elif "://" in requested_uri or requested_uri.startswith("www."):
            content, ctype = fetch_external_content(requested_uri)
            
            cache_filename = sanitize_cache_name(requested_uri)
            cache_path = os.path.join(FILES_DIRECTORY, cache_filename)
            try:
                with open(cache_path, "wb") as f:
                    f.write(content)

                print(f"[App Server] Cached new site to: {cache_filename}")

            except Exception as e:
                print(f"[App Server] Failed to cache: {e}")

            response = build_http_response(200, "OK", ctype, content)
            
        else:
            response = build_http_response(404, "Not Found", "text/html", b"<h1>404 File Not Found</h1>")

        client_sock.sendall(response)

    except Exception as e:
        print(f"[App Server Error] {e}")
        
    finally:
        client_sock.close()