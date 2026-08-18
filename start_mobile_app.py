import socket
import sys
from pathlib import Path
import qrcode
import uvicorn

def get_local_ip():
    """Finds the local network IP address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to an external IP to determine local interface IP (doesn't send data)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def main():
    local_ip = get_local_ip()
    port = 8000
    local_url = f"http://localhost:{port}"
    mobile_url = f"http://{local_ip}:{port}"

    print("=" * 65)
    print(" 🚀 NEXUS ALLOCATE PRO - MOBILE WEB SERVER 🚀")
    print("=" * 65)
    print(f" 💻 PC Local Access  : {local_url}")
    print(f" 📱 Phone Access (Wi-Fi): {mobile_url}")
    print("=" * 65)
    print("\n 📲 SCAN QR CODE WITH YOUR PHONE CAMERA TO OPEN APP:\n")

    # Generate ASCII QR Code
    qr = qrcode.QRCode(version=1, border=1)
    qr.add_data(mobile_url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    print("=" * 65)
    print(" Starting Uvicorn Web Server... Press Ctrl+C to stop.\n")

    uvicorn.run("web_app:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
