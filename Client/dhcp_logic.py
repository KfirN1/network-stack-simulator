import socket
from Shared.config import *

def run_dhcp_client_logic():
    # Performing a full DORA process (Discover, Offer, Request, Ack) to obtain an IP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(DHCP_TIMEOUT)
        server_address = (LOCALHOST, DHCP_SERVER_PORT)

        try:
            # 1. Discover
            print(f"[DHCP Client] Sending {DHCP_DISCOVER} for {CLIENT_ID}...")
            discover_msg = f"{DHCP_DISCOVER}|{CLIENT_ID}"
            sock.sendto(discover_msg.encode(), server_address)

            # 2. Offer
            data, sender_address = sock.recvfrom(MAX_BUFFER_SIZE)
            message = data.decode()

            if message.startswith(DHCP_OFFER):
                offered_ip = message.split(":")[1]
                print(f"[DHCP Client] Received offer: {offered_ip} from {sender_address}")

                # 3. Request
                print(f"[DHCP Client] Sending {DHCP_REQUEST} for {offered_ip}...")
                request_msg = f"{DHCP_REQUEST}|{CLIENT_ID}|{offered_ip}"
                sock.sendto(request_msg.encode(), server_address)

                # 4. Ack
                data, sender_address = sock.recvfrom(MAX_BUFFER_SIZE)
                ack_message = data.decode()

                if ack_message.startswith(DHCP_ACK):
                    parts = ack_message.split("|")
                    ip = parts[1].split(":")[1]
                    mask = parts[2].split(":")[1]
                    gw = parts[3].split(":")[1]
                    dns = parts[4].split(":")[1]
                    lease = parts[5].split(":")[1]

                    print("\n" + "="*40)
                    print("   DHCP ASSIGNMENT SUCCESSFUL")
                    print("="*40)
                    print(f" Assigned IP:  {ip}")
                    print(f" Subnet Mask:  {mask}")
                    print(f" Gateway:      {gw}")
                    print(f" DNS Server:   {dns}")
                    print(f" Lease Time:   {lease}s")
                    print("="*40 + "\n")
                    
                    return ip, sender_address 
                
        except socket.timeout:
            print("[DHCP Client] Error: The server did not respond (Timeout).")
        except Exception as e:
            print(f"[DHCP Client] Unexpected error: {e}")

    return None, None

def renew_lease(assigned_ip, server_address):
    # Sending a Request to the DHCP server to renew the lease (Renew)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2.0)
            renew_msg = f"{DHCP_REQUEST}|{CLIENT_ID}|{assigned_ip}"
            sock.sendto(renew_msg.encode(), server_address)
            
            data, _ = sock.recvfrom(MAX_BUFFER_SIZE)
            if data.decode().startswith(DHCP_ACK):
                return True
    except Exception:
        return False
    return False

def release_ip(assigned_ip, server_address):
    # Sending a Release message to the server to release the address (occurs in 'q')
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            release_msg = f"DHCP_RELEASE|{CLIENT_ID}|{assigned_ip}"
            sock.sendto(release_msg.encode(), server_address)
            print(f"[DHCP Client] IP {assigned_ip} released successfully back to pool.")
    except Exception as e:
        print(f"[DHCP Client] Failed to send Release: {e}")