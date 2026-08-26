# -*- coding: utf-8 -*-
"""
看门狗服务 - 负责启动/探测主 Dashboard 服务 (option_server.py, 8899)
端口: 8900
接口:
  GET  /api/status -> {server_alive: bool, port: 8899}
  POST /api/start  -> 若8899未运行则启动之, 返回结果
用途: dashboard 页面上的"启动服务"按钮调用此服务
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8900
MAIN_PORT = 8899
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(BASE_DIR, "option_server.py")
PYTHON = sys.executable  # 当前解释器(venv python), 与主服务同环境


def probe_main():
    """探测主服务 8899 是否存活"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:{}/api/status".format(MAIN_PORT), timeout=2) as r:
            if r.status == 200:
                return True
    except Exception:
        pass
    return False


def start_main():
    """启动主服务 (无窗口子进程)"""
    try:
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen(
            [PYTHON, MAIN_SCRIPT],
            cwd=BASE_DIR,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 等待最多 6 秒探测
        for _ in range(12):
            time.sleep(0.5)
            if probe_main():
                return True, "主服务已启动 (pid={})".format(proc.pid)
        return False, "启动命令已执行但服务未就绪 (pid={})".format(proc.pid)
    except Exception as e:
        return False, "启动失败: {}".format(str(e))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """CORS preflight: 跨域 POST 前浏览器会先发 OPTIONS"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self._send_json({"server_alive": probe_main(), "port": MAIN_PORT, "watchdog_port": PORT})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/start":
            if probe_main():
                self._send_json({"ok": True, "message": "主服务已在运行"})
                return
            ok, msg = start_main()
            self._send_json({"ok": ok, "message": msg, "server_alive": probe_main()})
        else:
            self._send_json({"error": "not found"}, 404)


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print("Watchdog running at http://127.0.0.1:{}/".format(PORT))
    server.serve_forever()


if __name__ == "__main__":
    main()
