import socket
import os
import re
import webbrowser
from Shared.config import *

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def download_file_tcp(filename, server_ip, assigned_ip):
    pid = os.getpid()
    
    temp_filename = f"temp_view_{pid}.html"
    save_path = os.path.join("downloads", temp_filename)

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(7.0) 
            sock.connect((server_ip, HTTP_PORT_TCP))

            request = (f"GET {filename} HTTP/1.1\r\n"
                       f"Host: {server_ip}\r\n"
                       f"X-Assigned-IP: {assigned_ip}\r\n" 
                       f"Connection: close\r\n\r\n")
            
            sock.sendall(request.encode())

            print(f"[TCP Client {pid}] Request sent for: {filename} (Identity: {assigned_ip})")
            
            response = b""
            while True:
                chunk = sock.recv(MAX_BUFFER_SIZE)
                if not chunk:
                    break
                response += chunk

            if b"\r\n\r\n" in response:
                header, body = response.split(b"\r\n\r\n", 1)
                header_text = header.decode(errors='ignore')

                if "200 OK" in header_text:
                    with open(save_path, "wb") as f:
                        f.write(body)

                    print(f"[TCP Client {pid}] Successfully received content")
                    
                    full_path = os.path.abspath(save_path)
                    webbrowser.open(f"file://{full_path}")
                    
                elif "404" in header_text:
                    print(f"[TCP Client {pid}] Error 404: The server/gateway could not find the resource.")
                    
                else:
                    status_line = header_text.splitlines()[0]
                    print(f"[TCP Client {pid}] Server returned: {status_line}")

            else:
                print(f"[TCP Client {pid}] Error: Received invalid HTTP response.")

    except socket.timeout:
        print(f"[TCP Client {pid}] Error: Connection timed out.")
        
    except Exception as e:
        print(f"[TCP Client {pid}] Unexpected Error: {e}")