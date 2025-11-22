from app import app
from waitress import serve
import socket


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable, just finding local IP
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


if __name__ == "__main__":
    local_ip = get_ip()
    print(f"🚀 Server Starting...")
    print(f"   - Local Access: http://localhost:5001")
    print(f"   - LAN Access:   http://{local_ip}:5001")
    print(f"   - Threads:      6")

    # '0.0.0.0' forces IPv4 to fix Cloudflare 502 errors
    # 'url_scheme=https' tells Flask to trust Cloudflare's SSL
    serve(app, host='0.0.0.0', port=5001, threads=6, url_scheme='https')