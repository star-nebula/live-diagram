#!/usr/bin/env python3
"""live-diagram 命令行：把一份 JSON 配置渲染成 H.264 mp4，或对它做逐帧版面自检。

  python scripts/livediagram.py render --config 配置.json --out 成片.mp4
  python scripts/livediagram.py check  --config 配置.json --out-dir frames --repeat
  python scripts/livediagram.py build  --config 配置.json --out page.html   # 生成可在浏览器直接打开的动态网页

依赖：Python 3.8+（仅标准库）、Chrome/Chromium/Edge、ffmpeg。跨平台（Windows/macOS/Linux）。
原理：把配置内嵌进 assets/template.html 生成自包含页面；页面暴露 window.seek(t)，
每一帧都是 t 的纯函数 —— 逐帧 seek + 截图，管道喂给 ffmpeg 合成；check 子命令
在采样时刻做 DOM 版面测量并验证回放的像素一致性。
"""
import argparse, base64, hashlib, hmac, json, os, shutil, socket, struct, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "assets" / "template.html"
CANVAS_PRESETS = {"4:5": (1200, 1500), "3:4": (1080, 1440), "1:1": (1080, 1080),
                  "9:16": (1080, 1920), "16:9": (1920, 1080)}

# ---------------------------------------------------------------- 可执行文件查找
def find_exe(explicit, names, what):
    if explicit:
        p = shutil.which(explicit) or (explicit if os.path.exists(explicit) else None)
        if p:
            return p
        sys.exit(f"[live-diagram] 找不到 {what}: {explicit}")
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    sys.exit(f"[live-diagram] 在 PATH 上找不到 {what}（试过 {', '.join(names)}）；可用 --chrome/--ffmpeg 显式指定")


CHROME_CANDIDATE_PATHS = [
    # Windows 常见安装位置
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"]


def find_chrome(explicit=None):
    if explicit:
        return find_exe(explicit, CHROME_NAMES, "Chrome")
    for n in CHROME_NAMES:
        p = shutil.which(n)
        if p:
            return p
    for p in CHROME_CANDIDATE_PATHS:
        if os.path.exists(p):
            return p
    sys.exit("[live-diagram] 找不到 Chrome/Chromium/Edge；用 --chrome 指定可执行文件路径")


def find_ffmpeg(explicit=None):
    return find_exe(explicit, ["ffmpeg"], "ffmpeg")


# ---------------------------------------------------------------- 配置与页面
def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def canvas(cfg):
    """(width, height, duration, fps)：显式 width/height 优先于 preset。"""
    cv = cfg.get("canvas", {})
    pw, ph = CANVAS_PRESETS.get(cv.get("preset"), (1200, 1500))
    return int(cv.get("width", pw)), int(cv.get("height", ph)), float(cv.get("duration", 30)), int(cv.get("fps", 30))


def build_page(config_path, out_path, template=None):
    """模板 + 配置 → 自包含 HTML。返回配置 dict。"""
    cfg = load_config(config_path)
    tpl = Path(template or DEFAULT_TEMPLATE).read_text(encoding="utf-8")
    if "<!--CONFIG-->" not in tpl:
        sys.exit("[live-diagram] 模板缺少 <!--CONFIG--> 占位符")
    blob = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
    tag = f'<script id="app-config" type="application/json">{blob}</script>'
    Path(out_path).write_text(tpl.replace("<!--CONFIG-->", tag), encoding="utf-8")
    return cfg


# ---------------------------------------------------------------- 最小 DevTools WebSocket 客户端（仅标准库）
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WS:
    """极简 WebSocket 文本帧客户端：掩码发送、分片接收、ping/pong。"""

    def __init__(self, host, port, path, timeout=60):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.s.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.s.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.s.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket 握手被关闭")
            buf += chunk
        head, self.buf = buf.split(b"\r\n\r\n", 1)
        status = head.split(b"\r\n")[0]
        if b"101" not in status:
            raise RuntimeError("WebSocket 握手失败: " + status.decode(errors="replace"))
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest())
        lines = head.split(b"\r\n")
        got = next((l.split(b":", 1)[1].strip() for l in lines
                    if l.lower().startswith(b"sec-websocket-accept")), b"")
        if not hmac.compare_digest(got, accept):
            raise RuntimeError("WebSocket 握手校验失败（Sec-WebSocket-Accept 不匹配）")

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.s.recv(1 << 20)
            if not chunk:
                raise RuntimeError("WebSocket 连接被对端关闭")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        p = text.encode()
        n = len(p)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(p))
        if n < 126:
            hdr = struct.pack("!BB", 0x81, 0x80 | n)
        elif n < 1 << 16:
            hdr = struct.pack("!BBH", 0x81, 0x80 | 126, n)
        else:
            hdr = struct.pack("!BBQ", 0x81, 0x80 | 127, n)
        self.s.sendall(hdr + mask + masked)

    def recv_msg(self):
        frags = []
        while True:
            b1, b2 = self._read(2)
            fin, op = b1 & 0x80, b1 & 0x0F
            masked = b2 & 0x80
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read(8))[0]
            mk = self._read(4) if masked else None
            data = self._read(n)
            if mk:
                data = bytes(b ^ mk[i % 4] for i, b in enumerate(data))
            if op == 9:  # ping → pong
                self._pong(data)
                continue
            if op == 8:
                raise RuntimeError("WebSocket 收到关闭帧")
            if op in (1, 0):
                frags.append(data)
                if fin:
                    return b"".join(frags).decode()
            # 二进制帧等其他类型：忽略

    def _pong(self, payload):
        n = len(payload)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        hdr = struct.pack("!BB", 0x8A, 0x80 | n) if n < 126 else struct.pack("!BBH", 0x8A, 0x80 | 126, n)
        self.s.sendall(hdr + mask + masked)


class Browser:
    """无头 Chrome：临时用户目录 + --remote-debugging-port=0，从 DevToolsActivePort 读真实端口。"""

    def __init__(self, chrome, width, height, no_sandbox=False):
        self.tmp = tempfile.mkdtemp(prefix="live-diagram-")
        args = [chrome, "--headless=new", "--remote-debugging-port=0",
                f"--user-data-dir={self.tmp}", "--no-first-run", "--no-default-browser-check",
                "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                "--font-render-hinting=none", "--allow-file-access-from-files",
                "--disable-background-timer-throttling", "--mute-audio",
                f"--window-size={width},{height}", "about:blank"]
        if no_sandbox:
            args.insert(1, "--no-sandbox")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port = self._wait_port()
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10) as r:
            targets = json.load(r)
        page = next((t for t in targets if t.get("type") == "page"), None)
        if not page or "webSocketDebuggerUrl" not in page:
            sys.exit("[live-diagram] DevTools 目标列表里没有可用的页面")
        path = "/" + page["webSocketDebuggerUrl"].split("/", 3)[3]
        self.ws = WS("127.0.0.1", port, path)
        self.n = 0
        self.call("Page.enable")
        self.call("Emulation.setDeviceMetricsOverride",
                  {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})

    def _wait_port(self, timeout=25):
        pf = os.path.join(self.tmp, "DevToolsActivePort")
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.proc.poll() is not None:
                sys.exit(f"[live-diagram] Chrome 启动即退出（exit={self.proc.returncode}）")
            if os.path.exists(pf):
                try:
                    return int(open(pf).readline().strip())
                except (ValueError, OSError):
                    pass  # Chrome 可能仍在写该文件，稍后重试
            time.sleep(0.15)
        sys.exit("[live-diagram] 等待 DevTools 端口超时（Chrome 是否正常启动？）")

    def call(self, method, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv_msg())
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})

    def eval(self, expr):
        r = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in r:
            raise RuntimeError("js error: " + json.dumps(r["exceptionDetails"], ensure_ascii=False)[:500])
        return r.get("result", {}).get("value")

    def open(self, url, timeout=25):
        self.call("Page.navigate", {"url": url})
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.eval("window.__ready===true"):
                    return
                if self.eval("typeof window.seek==='function' && (window.__error||'')!==''"):
                    raise RuntimeError("页面错误: " + str(self.eval("window.__error")))
                if self.eval("document.readyState") == "complete" and \
                   self.eval("typeof window.seek") == "undefined" and time.time() - t0 > 8:
                    raise RuntimeError("页面脚本没有初始化（模板损坏或 JSON 配置非法）")
            except RuntimeError as e:
                if "页面错误" in str(e) or "模板损坏" in str(e):
                    raise
            time.sleep(0.1)
        raise RuntimeError("页面在超时内未就绪（检查配置 JSON 是否合法）")

    def seek(self, t):
        self.eval(f"window.seek({t!r})")

    def shot(self):
        return base64.b64decode(self.call("Page.captureScreenshot", {"format": "png"})["data"])

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(8)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def page_url(page_path, extra=""):
    return Path(page_path).resolve().as_uri() + ("?" + extra if extra else "")


# ---------------------------------------------------------------- render
def cmd_render(a):
    chrome = find_chrome(a.chrome)
    ffmpeg = find_ffmpeg(a.ffmpeg)
    tmpdir = tempfile.mkdtemp(prefix="live-diagram-page-")
    page = a.html_out or os.path.join(tmpdir, "page.html")
    cfg = build_page(a.config, page, a.template)
    cw, ch, cdur, cfps = canvas(cfg)
    w = a.width or cw
    h = a.height or ch
    fps = a.fps or cfps
    dur = a.duration or cdur
    n = int(round(fps * dur))
    w -= w % 2
    h -= h % 2  # yuv420p 要求偶数尺寸
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps),
           "-c:v", "png", "-i", "-"]
    if a.audio == "silent":
        # 静音 AAC 轨：部分聊天应用会把无音轨 mp4 当成 GIF 处理
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest", "-c:a", "aac", "-b:a", "32k"]
    cmd += ["-c:v", "libx264", "-preset", a.preset, "-crf", str(a.crf), "-pix_fmt", "yuv420p",
            "-r", str(fps), "-movflags", "+faststart", a.out]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    if a.keep_frames:
        os.makedirs(a.keep_frames, exist_ok=True)
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Browser(chrome, w, h, a.no_sandbox) as br:
        br.open(page_url(page, "manual"))
        for i in range(n):
            br.seek(i / fps)
            png = br.shot()
            if a.keep_frames:
                Path(a.keep_frames, f"f_{i:04d}.png").write_bytes(png)
            ff.stdin.write(png)
            if i % fps == 0:
                print(f"\r{i}/{n} 帧", end="", file=sys.stderr, flush=True)
        err = br.eval("window.__error||''")
        if err:
            print("\n页面错误:", err, file=sys.stderr)
    ff.stdin.close()
    rc = ff.wait()
    if not a.html_out:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"\n已写出 {a.out}（{n} 帧，{w}x{h}@{fps}）", file=sys.stderr)
    sys.exit(rc)


# ---------------------------------------------------------------- check
TOL_PIXELS = 50  # 允许的可见差异像素数（亚像素抗锯齿噪声）；真实状态差异是数千像素级


def pixel_diff(br, a_png, b_png, delta=24):
    """在浏览器内比较两张 PNG：任一通道差值超过 delta 的像素数，以及最大差值。"""
    ja = base64.b64encode(a_png).decode()
    jb = base64.b64encode(b_png).decode()
    js = ('(async()=>{const L=s=>new Promise(r=>{const i=new Image();i.onload=()=>r(i);'
          "i.src='data:image/png;base64,'+s});"
          'const A=await L(%r),B=await L(%r),c=document.createElement("canvas");'
          "c.width=A.width;c.height=A.height;const x=c.getContext('2d');"
          "x.drawImage(A,0,0);const da=x.getImageData(0,0,c.width,c.height).data;"
          "x.clearRect(0,0,c.width,c.height);x.drawImage(B,0,0);"
          "const db=x.getImageData(0,0,c.width,c.height).data;"
          "let n=0,m=0;for(let i=0;i<da.length;i+=4){"
          "const d=Math.max(Math.abs(da[i]-db[i]),Math.abs(da[i+1]-db[i+1]),Math.abs(da[i+2]-db[i+2]));"
          'if(d>m)m=d;if(d>%d)n++}return [n,m]})()') % (ja, jb, delta)
    return br.eval(js)


def cmd_check(a):
    chrome = find_chrome(a.chrome)
    os.makedirs(a.out_dir, exist_ok=True)
    page = os.path.join(tempfile.mkdtemp(prefix="live-diagram-page-"), "page.html")
    cfg = build_page(a.config, page, a.template)
    w, h, dur, _ = canvas(cfg)
    times = [dur * i / a.samples + 0.011 * i for i in range(a.samples)]
    shots = [dur * (i + 0.5) / a.png for i in range(a.png)]
    problems = {}
    same = True
    with Browser(chrome, w, h, a.no_sandbox) as br:
        br.open(page_url(page, "manual"))
        for t in times + shots:
            br.seek(t)
            for p in br.eval("window.__check()"):
                problems.setdefault(p, []).append(round(t, 2))
        err = br.eval("window.__error||''")
        if err:
            problems["页面错误: " + err] = [0]
        for i, t in enumerate(shots):
            name = Path(a.out_dir) / f"frame_{i + 1}_t{t:05.2f}.png"
            br.seek(t)
            png = br.shot()
            if not a.video:
                name.write_bytes(png)
            if a.repeat:
                br.seek((t + dur / 2) % dur)
                br.shot()
                br.seek(t)
                again = br.shot()
                n_diff, mx = pixel_diff(br, png, again)
                ok = n_diff <= TOL_PIXELS
                same &= ok
                print(f"回放 t={t:.2f}s: {n_diff} 个像素可见差异（最大通道差 {mx}）→ "
                      f"{'一致' if ok else '不一致！'}")
    if a.video:
        ffmpeg = find_ffmpeg(a.ffmpeg)
        for i, t in enumerate(shots):
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", a.video,
                            "-frames:v", "1", str(Path(a.out_dir) / f"frame_{i + 1}_t{t:05.2f}.png")], check=True)
    for p, ts in problems.items():
        print(f"问题: {p}  （首次出现 t={ts[0]}s，{len(ts)}/{a.samples + a.png} 个采样点）")
    print(f"共检查 {a.samples + a.png} 个时间点，{len(problems)} 类问题；PNG 在 {a.out_dir}")
    if a.repeat and not same:
        sys.exit(1)
    sys.exit(1 if problems else 0)


# ---------------------------------------------------------------- build
def cmd_build(a):
    cfg = build_page(a.config, a.out, a.template)
    w, h, dur, fps = canvas(cfg)
    print(f"已生成 {a.out}（{w}x{h}，{dur}s@{fps}）。浏览器直接打开即为动态页面；"
          f"追加 ?t=秒数 可定格某一帧；?manual 停在 t=0。")


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--config", required=True, help="JSON 配置路径")
        p.add_argument("--template", help="替代模板路径（默认 assets/template.html）")
        p.add_argument("--chrome", help="Chrome/Chromium/Edge 可执行文件（默认自动查找）")
        p.add_argument("--no-sandbox", action="store_true", help="给 Chrome 传 --no-sandbox")

    pr = sub.add_parser("render", help="渲染成 H.264 mp4")
    common(pr)
    pr.add_argument("--out", required=True, help="输出 .mp4 路径")
    pr.add_argument("--width", type=int, help="覆盖画布宽")
    pr.add_argument("--height", type=int, help="覆盖画布高")
    pr.add_argument("--duration", type=float, help="覆盖时长（秒）")
    pr.add_argument("--fps", type=int, help="覆盖帧率")
    pr.add_argument("--crf", type=int, default=16, help="x264 CRF（默认 16；越高越清晰）")
    pr.add_argument("--preset", default="medium",
                    help="x264 预设（medium/slow/slower…，越慢压缩越好，默认 medium）")
    pr.add_argument("--ffmpeg", help="ffmpeg 路径（默认在 PATH 查找）")
    pr.add_argument("--audio", choices=["silent", "none"], default="silent",
                    help="silent=加静音 AAC 轨（默认，防止被当 GIF）；none=不加")
    pr.add_argument("--html-out", help="同时保留生成的自包含动态网页到此路径")
    pr.add_argument("--keep-frames", help="同时把 PNG 帧写入此目录")

    pc = sub.add_parser("check", help="逐时刻版面自检 + 导出 PNG + 回放一致性验证")
    common(pc)
    pc.add_argument("--out-dir", required=True, help="PNG 导出目录")
    pc.add_argument("--samples", type=int, default=120, help="DOM 测量的采样点数（默认 120）")
    pc.add_argument("--png", type=int, default=4, help="导出 PNG 张数（默认 4）")
    pc.add_argument("--repeat", action="store_true", help="每个导出点截两次图（中间跳到别处再跳回）并比对像素")
    pc.add_argument("--video", help="改为从该 mp4 切出 PNG（而不是从页面截图）")
    pc.add_argument("--ffmpeg", help="ffmpeg 路径（配合 --video）")

    pb = sub.add_parser("build", help="只生成自包含动态网页，不渲染视频")
    common(pb)
    pb.add_argument("--out", required=True, help="输出 .html 路径")

    a = ap.parse_args()
    {"render": cmd_render, "check": cmd_check, "build": cmd_build}[a.cmd](a)


if __name__ == "__main__":
    main()
