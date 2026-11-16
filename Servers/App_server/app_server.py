import socket
import threading
import os
import queue 
from Shared.config import *
from Servers.App_server.tcp_handler import handle_tcp_client
from Servers.App_server.rudp_handler import RUDPServerHandler

active_sessions = {}
sessions_lock = threading.Lock() 

def run_tcp_interface():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((LOCALHOST, HTTP_PORT_TCP))
        s.listen(10)
        print(f"[App Server] TCP Website Interface: http://{LOCALHOST}:{HTTP_PORT_TCP}")

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True).start()

def run_rudp_interface():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((LOCALHOST, HTTP_PORT_RUDP))
        print(f"[App Server] RUDP Dispatcher Online: {LOCALHOST}:{HTTP_PORT_RUDP}")

        while True:
            data, addr = s.recvfrom(MAX_BUFFER_SIZE + 64)
            
            with sessions_lock:
                try:
                    msg = data.decode(errors='ignore')
                    if msg.startswith("GET_RUDP|"):
                        parts = msg.split("|")
                        filename = parts[1]
                        assigned_ip = "Unknown"
                        
                        if len(parts) > 2 and parts[2].startswith("SRC_IP:"):
                            assigned_ip = parts[2].split(":")[1]
                        
                        client_queue = queue.Queue()
                        active_sessions[addr] = client_queue
                        
                        handler = RUDPServerHandler(s, addr, client_queue, assigned_ip=assigned_ip)
                        
                        def handle_and_cleanup(h, f, a):
                            h.send_file_rudp(f)
                            with sessions_lock:
                                if a in active_sessions:
                                    del active_sessions[a]
                                    print(f"[App Server] Session closed for {assigned_ip} ({a})")

                        threading.Thread(target=handle_and_cleanup, args=(handler, filename, addr), daemon=True).start()
                        continue
                except Exception as e:
                    print(f"[App Server Dispatcher Error] {e}")

                if addr in active_sessions:
                    active_sessions[addr].put(data)
                else:
                    print(f"[App Server] Dropping unsolicited packet from {addr}")

if __name__ == "__main__":
    if not os.path.exists(FILES_DIRECTORY):
        os.makedirs(FILES_DIRECTORY)
    
    index_path = os.path.join(FILES_DIRECTORY, "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("<html><body><h1>Welcome to My Project Website</h1><p>Accessible via TCP and RUDP!</p></body></html>")

    print("--- Application Server Launching (Dispatcher Mode) ---")
    threading.Thread(target=run_tcp_interface, daemon=True).start()
    run_rudp_interface()