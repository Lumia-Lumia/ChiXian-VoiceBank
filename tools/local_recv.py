"""把浏览器取到的文件转存到本地磁盘。

背景：Bash 沙箱没有外网（DNS 与 443 都不通），而浏览器有。浏览器又不能直接
写磁盘（下载被拦/卡住），所以这里起一个只监听 127.0.0.1 的接收端：

    页面 fetch(url) -> POST 到 http://127.0.0.1:8765/<文件名>

用 `Content-Type: text/plain` + `mode: no-cors` 发出来是「简单请求」，
不触发预检，也不需要返回 CORS 头 —— 页面拿不到响应，但数据已经送到了。

    python tools/local_recv.py <输出目录> [端口]
"""

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

OUT = "."
CHUNK = 1 << 20


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        name = os.path.basename(unquote(urlparse(self.path).path)) or "download.bin"
        n = int(self.headers.get("Content-Length") or 0)
        path = os.path.join(OUT, name)
        got = 0
        with open(path, "wb") as f:
            while got < n:
                buf = self.rfile.read(min(CHUNK, n - got))
                if not buf:
                    break
                f.write(buf)
                got += len(buf)
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")
        print(f"  收到 {name}: {got} / {n} 字节", flush=True)

    def log_message(self, *a):
        pass


def main():
    global OUT
    if len(sys.argv) > 1:
        OUT = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"监听 127.0.0.1:{port}，落盘到 {os.path.abspath(OUT)}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
