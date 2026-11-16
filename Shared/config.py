import os

'''
This file defines constant variables and dynamic paths for the project.
'''

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOCALHOST = "127.0.0.1"
CLIENT_ID = "KFIR-PC"
MAX_BUFFER_SIZE = 1024
MAX_UDP_SIZE = 65535

# DHCP variables
DHCP_TIMEOUT = 5.0
DHCP_SERVER_PORT = 67
DHCP_CLIENT_PORT = 68
DHCP_BASE_IP = "192.168.1."
DHCP_POOL_START = 100
DHCP_POOL_END = 200
DHCP_LEASE_TIME = 60
DHCP_SUBNET_MASK = "255.255.255.0"
DHCP_GATEWAY = "192.168.1.1"

DHCP_DISCOVER = "DHCP_DISCOVER"
DHCP_OFFER = "DHCP_OFFER"
DHCP_REQUEST = "DHCP_REQUEST"
DHCP_ACK = "DHCP_ACK"

# DNS variables
DNS_PORT = 53
DNS_SERVER_IP = "127.0.0.1"
APP_SERVER_NAME = "www.my-app-server.com"
APP_SERVER_IP = "127.0.0.1"
DNS_TIMEOUT = 5.0
DNS_HTTP_PORT = 8081
DNS_TYPE_A = "A"
DNS_TYPE_CNAME = "CNAME"

# HTTP variables
HTTP_PORT_TCP = 80
HTTP_PORT_RUDP = 8080

# RUDP variables
RUDP_TIMEOUT = 5.0
RUDP_WINDOW_SIZE = 5
RUDP_HEADER_SIZE = 8


DHCP_DB_PATH = os.path.join(BASE_DIR, "Servers", "DHCP_server", "dhcp_leases.json")
DNS_DB_PATH = os.path.join(BASE_DIR, "Servers", "DNS_server", "dns_cache.json")

FILES_DIRECTORY = os.path.join(BASE_DIR, "Servers", "App_server", "files")

if not os.path.exists(FILES_DIRECTORY):
    os.makedirs(FILES_DIRECTORY)

DOWNLOADS_DIRECTORY = os.path.join(BASE_DIR, "Client", "downloads")

if not os.path.exists(DOWNLOADS_DIRECTORY):
    os.makedirs(DOWNLOADS_DIRECTORY)