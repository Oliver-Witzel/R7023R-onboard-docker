import socket
from spacepackets.ccsds.spacepacket import SpacePacketHeader

HOST, PORT = "0.0.0.0", 5000
HEADER_LEN = 6

def recv_exact(conn: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed connection")
        buf.extend(chunk)
    return bytes(buf)

def recv_packet(conn: socket.socket) -> bytes:
    header_raw = recv_exact(conn, HEADER_LEN)
    header = SpacePacketHeader.unpack(header_raw)
    # CCSDS data length field = (bytes after primary header) - 1
    rest = recv_exact(conn, header.data_len + 1)
    return header_raw + rest

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"listening on {PORT}", flush=True)
    while True:
        conn, addr = srv.accept()
        print("connection from", addr, flush=True)
        with conn:
            try:
                while True:
                    raw = recv_packet(conn)
                    hdr = SpacePacketHeader.unpack(raw[:HEADER_LEN])
                    payload = raw[HEADER_LEN:]
                    print(f"APID={hdr.apid} seq={hdr.seq_count} "
                          f"type={hdr.packet_type.name} payload={payload!r}",
                          flush=True)
            except ConnectionError:
                print("sender disconnected", flush=True)