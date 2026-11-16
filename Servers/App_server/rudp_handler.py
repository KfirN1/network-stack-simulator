import socket
import os
import queue
from Shared.config import *
from Shared.utils import (
    create_packet, parse_packet, FLAG_ACK, FLAG_FIN, 
    fetch_external_content, sanitize_cache_name
)

class RUDPServerHandler:
    def __init__(self, sock: socket.socket, client_address, client_queue: queue.Queue, assigned_ip="Unknown"):
        self.sock = sock
        self.client_address = client_address
        self.client_queue = client_queue 
        self.assigned_ip = assigned_ip  

        # Congestion Control - AIMD
        self.cwnd = 1.0
        self.ssthresh = 64
        self.dup_acks = 0

        # Sliding Window
        self.base = 0
        self.next_seq = 0
        self.packets = []
        
        # Flow Control
        self.rwnd = RUDP_WINDOW_SIZE

    def send_file_rudp(self, filename):
        self.filename = filename
        self.packets = [] 
        
        print(f"\n[RUDP Server] New Session: Client {self.assigned_ip} ({self.client_address})")
        print(f"[RUDP Server] Request for: '{filename}'")

        cache_name = sanitize_cache_name(filename)
        filepath = os.path.join(FILES_DIRECTORY, cache_name)
        original_filepath = os.path.join(FILES_DIRECTORY, filename)

        if os.path.exists(filepath) and os.path.isfile(filepath):
            print(f"[RUDP Server] Cache Hit! Serving: '{cache_name}'")
            with open(filepath, "rb") as f:
                content = f.read()
        elif os.path.exists(original_filepath) and os.path.isfile(original_filepath):
            print(f"[RUDP Server] Cache Hit! Serving: '{filename}'")
            with open(original_filepath, "rb") as f:
                content = f.read()
        elif "://" in filename or filename.startswith("www."):
            content, _ = fetch_external_content(filename)
            cache_path = os.path.join(FILES_DIRECTORY, cache_name)
            try:
                with open(cache_path, "wb") as f:
                    f.write(content)
            except Exception as e:
                print(f"[RUDP Server] Cache Error: {e}")
        else:
            content = f"<h1>404 Not Found</h1><p>{filename} is not available.</p>".encode()

        self.packets = [content[i:i+MAX_BUFFER_SIZE] for i in range(0, len(content), MAX_BUFFER_SIZE)]
        print(f"[RUDP Server] Starting Pipelined Transmission to {self.assigned_ip}: {len(self.packets)} packets.")
            
        self._main_transmission_loop()

    def _main_transmission_loop(self):
        total_packets = len(self.packets)

        while self.base < total_packets:
            effective_window = min(int(self.cwnd), self.rwnd)

            while self.next_seq < self.base + effective_window and self.next_seq < total_packets:
                data = self.packets[self.next_seq]
                packet = create_packet(self.next_seq, 0, 0, self.rwnd, data)
                self.sock.sendto(packet, self.client_address)
                self.next_seq += 1

            try:
                ack_packet_data = self.client_queue.get(timeout=RUDP_TIMEOUT)
                header, _ = parse_packet(ack_packet_data)

                if header and header["is_ack"]:
                    ack_num = header["ack"]
                    self.rwnd = header["win"] 

                    if ack_num > self.base:
                        self._handle_new_ack(ack_num) 
                    elif ack_num == self.base:
                        self._handle_duplicate_ack()
                    
            except queue.Empty:
                print(f"[RUDP Server] Timeout for {self.assigned_ip}. Retransmitting from {self.base}")
                self._handle_timeout()

        fin_packet = create_packet(self.next_seq, 0, FLAG_FIN, self.rwnd)
        self.sock.sendto(fin_packet, self.client_address)
        print(f"[RUDP Server] Successfully finished sending {self.filename} to {self.assigned_ip}")

    def _handle_new_ack(self, ack_num):
        self.base = ack_num
        self.dup_acks = 0
        if self.cwnd < self.ssthresh:
            self.cwnd += 1 
        else: 
            self.cwnd += 1 / int(self.cwnd) 

    def _handle_duplicate_ack(self):
        self.dup_acks += 1
        if self.dup_acks == 3:
            print(f"[RUDP Server] Triple duplicate ACK from {self.assigned_ip}! Fast Retransmit.")
            self.next_seq = self.base

    def _handle_timeout(self):
        self.ssthresh = max(int(self.cwnd / 2), 2)
        self.cwnd = 1.0
        self.next_seq = self.base