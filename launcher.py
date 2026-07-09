from __future__ import annotations

import ipaddress
import re
import socket
import subprocess
import threading
import time
import webbrowser

from app import app, ensure_data_files


HOST = "0.0.0.0"
PORT = 5000


def is_usable_private_ipv4(ip_text: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False

    return (
        ip.version == 4
        and ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
    )


def get_ips_from_socket() -> set[str]:
    ips: set[str] = set()

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if is_usable_private_ipv4(ip):
                ips.add(ip)
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if is_usable_private_ipv4(ip):
                ips.add(ip)
    except OSError:
        pass

    return ips


def get_ips_from_ipconfig() -> set[str]:
    ips: set[str] = set()

    try:
        result = subprocess.run(
            ["ipconfig"],
            capture_output=True,
            text=True,
            encoding="cp932",
            errors="ignore",
            check=False,
        )
    except OSError:
        return ips

    output = result.stdout or ""

    for match in re.finditer(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", output):
        ip = match.group(0)
        if is_usable_private_ipv4(ip):
            ips.add(ip)

    return ips


def get_local_ips() -> list[str]:
    ips: set[str] = set()

    ips.update(get_ips_from_socket())
    ips.update(get_ips_from_ipconfig())

    def sort_key(ip_text: str) -> tuple[int, str]:
        if ip_text == "192.168.137.1":
            return (0, ip_text)
        if ip_text.startswith("192.168."):
            return (1, ip_text)
        if ip_text.startswith("10."):
            return (2, ip_text)
        if ip_text.startswith("172."):
            return (3, ip_text)
        return (9, ip_text)

    sorted_ips = sorted(ips, key=sort_key)

    if not sorted_ips:
        return ["127.0.0.1"]

    return sorted_ips


def open_admin_page() -> None:
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{PORT}/admin")


def print_startup_info() -> None:
    local_ips = get_local_ips()

    print("")
    print("========================================")
    print(" Local Table Order App")
    print("========================================")
    print("")
    print("管理画面URL（このPC用）:")
    print(f"  http://127.0.0.1:{PORT}/admin")
    print("")
    print("テーブル選択一覧URL（タブレット・スマホ用）:")
    print("  タブレットやスマホのブラウザで、下のURLを開いてください。")
    print("  いずれかのURLが有効の場合画面がテーブル選択画面が開きます")
    print("")

    for ip in local_ips:
        print(f"  http://{ip}:{PORT}/")

    print("")
    print("注意:")
    print("  127.0.0.1 はこのPC専用です。")
    print("  タブレットやスマホでは 192.168.x.x / 10.x.x.x / 172.x.x.x のURLを使ってください。")
    print("")
    print("タブレットやスマホで開けない場合:")
    print("  1. サーバー用PCで PowerShell またはコマンドプロンプトを開く")
    print("  2. ipconfig と入力する")
    print("  3. IPv4 アドレスを確認する")
    print("  4. http://IPv4アドレス:5000/ をタブレットやスマホで開く")
    print("")
    print("この黒い画面を閉じるとアプリが終了します。")
    print("========================================")
    print("")


if __name__ == "__main__":
    ensure_data_files()
    print_startup_info()

    threading.Thread(target=open_admin_page, daemon=True).start()

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )