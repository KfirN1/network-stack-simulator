import sys
import os
import threading
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Client.dhcp_logic import run_dhcp_client_logic, renew_lease, release_ip
from Client.dns_logic import resolve_dns
from Client.tcp_logic import download_file_tcp
from Client.rudp_logic import download_file_rudp
from Shared.config import APP_SERVER_NAME, DHCP_LEASE_TIME

def dhcp_renewal_worker(assigned_ip, dhcp_server_addr, stop_event):
    # A background process that renews the lease with the server every half of the lease time
    renew_interval = DHCP_LEASE_TIME / 2
    while not stop_event.is_set():
        if stop_event.wait(renew_interval):
            break
            
        success = renew_lease(assigned_ip, dhcp_server_addr)
        if success:
            print(f"\n[DHCP Background] Lease renewed for {assigned_ip}")
        else:
            print(f"\n[DHCP Background] Warning: Failed to renew lease. Server might be down.")

def main():
    print("\n" + "=" * 50)
    print("--- Network Project Client Control Center ---")
    print("--- Identity-Aware Version (Assigned IP Integration) ---")
    print("=" * 50)

    # 1. DHCP
    assigned_ip, dhcp_server_addr = run_dhcp_client_logic()

    if not assigned_ip:
        print("DHCP Failed. Exiting.")
        return
    
    print(f"Status: Client is ONLINE with IP {assigned_ip}")

    stop_dhcp_thread = threading.Event()
    renewal_thread = threading.Thread(
        target=dhcp_renewal_worker, 
        args=(assigned_ip, dhcp_server_addr, stop_dhcp_thread),
        daemon=True 
    )
    renewal_thread.start()
 
    # 2. DNS 
    server_ip = resolve_dns(APP_SERVER_NAME, assigned_ip)

    if not server_ip:
        print("DNS Failed. Exiting.")
        stop_dhcp_thread.set()
        return
    
    print(f"--- Ready to connect to application server at {server_ip} ---")

    #3. HTTP
    try:
        while True:
            target = input("\nEnter file name or URL to fetch (or 'q' to quit): ").strip()

            if target.lower() == 'q': 
                print("[Client] Initiating graceful shutdown...")
                break

            if not target:
                continue

            print("Choose Protocol:")
            print("1. TCP (Standard HTTP)")
            print("2. RUDP (Reliable UDP)")

            choice = input("Your choice (1/2): ")

            if choice == "1":
                download_file_tcp(target, server_ip, assigned_ip)
            elif choice == "2":
                download_file_rudp(target, server_ip, assigned_ip)
            else:
                print("Invalid choice.")

    finally:
        # 4. Release
        stop_dhcp_thread.set() 
        if assigned_ip and dhcp_server_addr:
            release_ip(assigned_ip, dhcp_server_addr)
        print("--- Client Shut Down Successfully ---")

if __name__ == "__main__":
    main()