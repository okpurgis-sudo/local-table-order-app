from __future__ import annotations

import socket
import threading
import time
import webbrowser

from app import PORT, TABLE_COUNT, app, ensure_data_files, get_app_config

HOST = "0.0.0.0"


def get_local_ip() -> str:
    """
    タブレットからアクセスするためのサーバーPCのIPアドレスを取得する。
    失敗した場合は 127.0.0.1 を返す。
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def open_admin_page() -> None:
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{PORT}/admin")


def print_startup_info() -> None:
    local_ip = get_local_ip()
    app_config = get_app_config()

    print("")
    print("========================================")
    print(f" {app_config['display_name']} 起動中")
    print("========================================")
    print("")
    print("管理画面:")
    print(f"  http://127.0.0.1:{PORT}/admin")
    print("")
    print("タブレット用URL:")
    for table_no in range(1, TABLE_COUNT + 1):
        print(f"  テーブル {table_no}: http://{local_ip}:{PORT}/table/{table_no}")
    print("")
    print("終了するときは、この黒い画面を閉じてください。")
    print("========================================")
    print("")


if __name__ == "__main__":
    ensure_data_files()
    print_startup_info()
    threading.Thread(target=open_admin_page, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
