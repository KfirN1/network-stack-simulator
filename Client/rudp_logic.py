import socket
import os
import webbrowser
from Shared.config import *
from Shared.utils import create_packet, parse_packet, FLAG_ACK, FLAG_FIN

def download_file_rudp(filename, server_ip, assigned_ip):
    server_address = (server_ip, HTTP_PORT_RUDP)
    pid = os.getpid()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    downloads_dir = os.path.join(current_dir, "downloads")
    
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)

    _, extension = os.path.splitext(filename)
    if not extension:
        extension = ".html"
    
    temp_filename = f"temp_view_{pid}{extension}"
    save_path = os.path.join(downloads_dir, temp_filename)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(RUDP_TIMEOUT)

        request_msg = f"GET_RUDP|{filename}|SRC_IP:{assigned_ip}"
        
        sock.sendto(request_msg.encode(), server_address)
        print(f"[RUDP Client {pid}] Requesting {filename} via RUDP (Identity: {assigned_ip})...")

        expected_seq = 0
        file_data = b""
        receive_buffer = {}
        retries = 0
        MAX_REQUEST_RETRIES = 5

        while True:
            try:
                packet, addr = sock.recvfrom(MAX_BUFFER_SIZE + 64)
                header, data = parse_packet(packet)

                if not header:
                    continue

                retries = 0 

                if header["is_fin"]:
                    fin_ack = create_packet(0, header["seq"], FLAG_ACK, RUDP_WINDOW_SIZE)
                    sock.sendto(fin_ack, addr)
                    break

                seq_num = header["seq"]

                if seq_num == expected_seq:
                    file_data += data
                    expected_seq += 1
                    while expected_seq in receive_buffer:
                        file_data += receive_buffer.pop(expected_seq)
                        expected_seq += 1
                
                elif seq_num > expected_seq:
                    receive_buffer[seq_num] = data

                current_rwnd = RUDP_WINDOW_SIZE - len(receive_buffer)
                ack_packet = create_packet(0, expected_seq, FLAG_ACK, current_rwnd)
                sock.sendto(ack_packet, addr)

            except socket.timeout:
                if expected_seq == 0:
                    if retries < MAX_REQUEST_RETRIES:
                        retries += 1
                        print(f"[RUDP Client {pid}] Timeout! Resending initial request (Attempt {retries}/{MAX_REQUEST_RETRIES})...")
                        sock.sendto(request_msg.encode(), server_address)
                        continue
                    else:
                        print(f"[RUDP Client {pid}] Critical Error: Server not responding.")
                        break
                else:
                    print(f"[RUDP Client {pid}] Timeout! Still waiting for packet {expected_seq}...")
                    continue

            except Exception as e:
                print(f"[RUDP Client {pid}] Error: {e}")
                break

        if file_data:
            with open(save_path, "wb") as f:
                f.write(file_data)
            
            print(f"[RUDP Client {pid}] Download complete! Displaying: {temp_filename}")
            
            full_path = "file://" + os.path.abspath(save_path)
            webbrowser.open(full_path)
        else:
            print(f"[RUDP Client {pid}] No data received from server.")