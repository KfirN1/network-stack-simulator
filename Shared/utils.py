import struct
import urllib.request
import re

RUDP_HEADER_FORMAT = "!IIBHH"
RUDP_HEADER_SIZE = struct.calcsize(RUDP_HEADER_FORMAT)

FLAG_ACK = 0x01
FLAG_SYN = 0x02
FLAG_FIN = 0x04

def calculate_checksum(data):
    if len(data) % 2 == 1:
        data += b'\x00'
    s = 0

    for i in range(0, len(data), 2):
        w = (data[i] << 8) + (data[i + 1])
        s = s + w
        s = (s & 0xffff) + (s >> 16)
    return ~s & 0xffff

def create_packet(seq_num, ack_num, flags, window, data=b''):
    temp_header = struct.pack(RUDP_HEADER_FORMAT, seq_num, ack_num, flags, window, 0)
    packet_checksum = calculate_checksum(temp_header + data)
    final_header = struct.pack(RUDP_HEADER_FORMAT, seq_num, ack_num, flags, window, packet_checksum)
    return final_header + data

def parse_packet(packet):
    if len(packet) < RUDP_HEADER_SIZE:
        return None, None
    
    header_bytes = packet[:RUDP_HEADER_SIZE]
    data = packet[RUDP_HEADER_SIZE:]
    seq, ack, flags, win, recived_checksum = struct.unpack(RUDP_HEADER_FORMAT, header_bytes)
    temp_header = struct.pack(RUDP_HEADER_FORMAT, seq, ack, flags, win, 0)
    calculated_checksum = calculate_checksum(temp_header + data)

    if calculated_checksum != recived_checksum:
        print(f"[RUDP Utils] Checksum mismatch! Packet corrupted.")
        return None, None
    
    header_info = {
        "seq": seq, "ack": ack, "flags": flags, "win": win,
        "is_ack": bool(flags & FLAG_ACK),
        "is_syn": bool(flags & FLAG_SYN),
        "is_fin": bool(flags & FLAG_FIN)
    }
    return header_info, data

def sanitize_cache_name(url):
    clean = re.sub(r'[\\/*?:"<>|]', '_', url)

    if not clean.lower().endswith(".html"): clean += ".html"
    return clean

def fetch_external_content(url):
    try:
        if not url.startswith("http"):
            original_url = "http://" + url
        else:
            original_url = url
            
        print(f"[Gateway Utils] Fetching (HTTP): {original_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
        }
        
        req = urllib.request.Request(original_url, headers=headers)

        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read()
            ctype = response.info().get_content_type()
            
            if "text/html" in ctype:
                html_str = content.decode(errors='ignore')
                base_tag = f'<base href="{original_url}/">'
                html_str = html_str.replace("<head>", f"<head>{base_tag}", 1) if "<head>" in html_str else base_tag + html_str
                content = html_str.encode()
            
            return content, ctype
        
    except Exception as e:
        return f"<h1>Gateway Error</h1><p>{e}</p>".encode(), "text/html"