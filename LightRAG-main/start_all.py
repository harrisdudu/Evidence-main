#!/usr/bin/env python3
"""
LightRAG 一键启动脚本

功能：
- 同时启动后端 API 服务和前端 WebUI 服务
- 支持后台运行和前台运行模式
- 提供服务状态检查和优雅关闭

使用方法：
    python start_all.py              # 前台启动（默认）
    python start_all.py --backend    # 仅启动后端
    python start_all.py --frontend    # 仅启动前端
    python start_all.py --check       # 检查服务状态
    python start_all.py --stop        # 停止所有服务
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import List, Optional

# ============================================================
# 配置项
# ============================================================

# 项目根目录（脚本所在目录）
PROJECT_ROOT = Path(__file__).parent.resolve()

# 后端配置
BACKEND_PORT = 9621  # 默认端口
BACKEND_HOST = "127.0.0.1"

# 前端配置
FRONTEND_PORT = 5173  # Vite 默认端口

# 服务进程列表
services: List[subprocess.Popen] = []


# 颜色输出
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_color(text: str, color: str = Colors.RESET):
    """带颜色打印"""
    print(f"{color}{text}{Colors.RESET}")


def print_header(text: str):
    """打印标题"""
    print_color(f"\n{'=' * 60}", Colors.BLUE)
    print_color(f"  {text}", Colors.BLUE)
    print_color(f"{'=' * 60}\n", Colors.BLUE)


def print_success(text: str):
    """打印成功信息"""
    print_color(f"✓ {text}", Colors.GREEN)


def print_error(text: str):
    """打印错误信息"""
    print_color(f"✗ {text}", Colors.RED)


def print_warning(text: str):
    """打印警告信息"""
    print_color(f"⚠ {text}", Colors.YELLOW)


def print_info(text: str):
    """打印信息"""
    print_color(f"ℹ {text}", Colors.BLUE)


# ============================================================
# 服务管理函数
# ============================================================


def check_port_available(port: int) -> bool:
    """检查端口是否可用"""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return True
    except OSError:
        return False


def check_service_running(port: int, path: str = "/docs") -> bool:
    """检查服务是否运行"""
    try:
        with urllib.request.urlopen(
            f"http://{BACKEND_HOST}:{port}{path}", timeout=2
        ) as resp:
            return 200 <= resp.status < 500
    except urllib.error.HTTPError as e:
        return 200 <= e.code < 500
    except Exception:
        return False


def get_backend_command() -> List[str]:
    """获取后端启动命令"""
    if shutil.which("uv"):
        return ["uv", "run", "lightrag-server"]
    return ["lightrag-server"]


def get_frontend_command() -> List[str]:
    """获取前端启动命令"""
    return ["bun", "run", "dev", "--", "--host", BACKEND_HOST, "--port", str(FRONTEND_PORT)]

def ensure_frontend_deps(frontend_dir: Path) -> bool:
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists():
        return True
    if not shutil.which("bun"):
        print_error("找不到 bun 命令，请确保已安装 Bun")
        print_info("参考: https://bun.sh/docs/installation")
        return False
    print_info("检测到前端依赖未安装，正在执行 bun install ...")
    try:
        subprocess.run(
            ["bun", "install", "--frozen-lockfile"],
            cwd=str(frontend_dir),
            check=True,
        )
        return True
    except Exception as e:
        print_error(f"前端依赖安装失败: {e}")
        return False


def wait_for_service(port: int, path: str, timeout_sec: int = 30) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if check_service_running(port, path):
            return True
        time.sleep(0.5)
    return False


def _parse_netstat_pids_for_port(port: int) -> List[int]:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []
        pids = set()
        for line in (result.stdout or "").splitlines():
            if f":{port} " not in line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            local_addr = parts[1]
            state = parts[3] if parts[0].upper() == "TCP" else None
            pid_str = parts[4] if parts[0].upper() == "TCP" else parts[-1]
            if f":{port}" not in local_addr:
                continue
            if state and state.upper() not in ("LISTENING", "ESTABLISHED", "TIME_WAIT", "CLOSE_WAIT"):
                continue
            try:
                pid = int(pid_str)
            except Exception:
                continue
            if pid > 0:
                pids.add(pid)
        return sorted(pids)
    except Exception:
        return []


def _psutil_pids_for_port(port: int) -> List[int]:
    try:
        import psutil  # type: ignore
    except Exception:
        return []
    pids = set()
    try:
        for c in psutil.net_connections(kind="tcp"):
            try:
                if not c.laddr:
                    continue
                if getattr(c.laddr, "port", None) != port:
                    continue
                if c.pid:
                    pids.add(int(c.pid))
            except Exception:
                continue
    except Exception:
        return []
    return sorted(pids)


def _kill_pid(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return True
        except Exception:
            return False
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except Exception:
        return False


def free_port(port: int, name: str) -> bool:
    if check_port_available(port):
        return True
    pids = _psutil_pids_for_port(port) or _parse_netstat_pids_for_port(port)
    if not pids:
        print_warning(f"端口 {port} 已被占用，未找到占用进程 ({name})")
        return False
    print_warning(f"端口 {port} 已被占用，尝试终止占用进程 ({name}): {', '.join(map(str, pids))}")
    ok = False
    for pid in pids:
        ok = _kill_pid(pid) or ok
    time.sleep(0.8)
    if check_port_available(port):
        print_success(f"端口 {port} 已释放 ({name})")
        return True
    print_error(f"端口 {port} 释放失败 ({name})")
    return ok



def start_backend() -> Optional[subprocess.Popen]:
    """启动后端服务"""

    if not check_port_available(BACKEND_PORT):
        free_port(BACKEND_PORT, "Backend")
        if not check_port_available(BACKEND_PORT):
            if check_service_running(BACKEND_PORT, "/docs"):
                print_warning(f"后端服务已在端口 {BACKEND_PORT} 运行")
                return None
            print_error(f"端口 {BACKEND_PORT} 已被占用")
            return None

    cmd = get_backend_command() + ["--host", BACKEND_HOST, "--port", str(BACKEND_PORT)]

    try:
        # 在项目根目录启动后端
        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=None,
            stderr=None,
            # Windows 下创建新进程组
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32"
            else 0,
        )

        # 等待服务启动
        print_info("等待后端服务启动...")

        # 检查服务是否成功启动
        if wait_for_service(BACKEND_PORT, "/health", timeout_sec=60):
            print_success(f"后端服务已启动: http://localhost:{BACKEND_PORT}")
            print_info(f"API 文档: http://localhost:{BACKEND_PORT}/docs")
            return process
        else:
            print_error("后端服务启动失败")
            return process

    except FileNotFoundError:
        print_error("找不到 lightrag-server 命令，请确保已安装 LightRAG")
        print_info("使用 pip install lightrag-hku[api] 安装")
        return None
    except Exception as e:
        print_error(f"启动后端服务失败: {e}")
        return None


def start_frontend() -> Optional[subprocess.Popen]:
    """启动前端服务"""
    print_info("正在启动前端 WebUI 服务...")

    if not check_port_available(FRONTEND_PORT):
        free_port(FRONTEND_PORT, "Frontend")
        if not check_port_available(FRONTEND_PORT):
            if check_service_running(FRONTEND_PORT):
                print_warning(f"前端服务已在端口 {FRONTEND_PORT} 运行")
                return None
            print_error(f"端口 {FRONTEND_PORT} 已被占用")
            return None

    frontend_dir = PROJECT_ROOT / "lightrag_webui"
    if not ensure_frontend_deps(frontend_dir):
        return None
    cmd = get_frontend_command()

    try:
        # 在前端目录启动
        process = subprocess.Popen(
            cmd,
            cwd=str(frontend_dir),
            stdout=None,
            stderr=None,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32"
            else 0,
        )

        # 等待服务启动
        print_info("等待前端服务启动...")

        # 检查服务是否成功启动
        if wait_for_service(FRONTEND_PORT, "/webui/", timeout_sec=60):
            print_success(f"前端服务已启动: http://localhost:{FRONTEND_PORT}/webui/")
            return process
        else:
            print_error("前端服务启动失败")
            return process

    except FileNotFoundError:
        print_error("找不到 bun 命令，请确保已安装 Bun")
        print_info("参考: https://bun.sh/docs/installation")
        return None
    except Exception as e:
        print_error(f"启动前端服务失败: {e}")
        return None


def stop_services():
    """停止所有服务"""
    print_header("停止服务")

    # 查找并停止相关进程
    try:
        import psutil
    except Exception:
        psutil = None

    stopped = []

    # 查找 lightrag-server 进程
    if psutil:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                if cmdline and any("lightrag" in str(c).lower() for c in cmdline):
                    proc.terminate()
                    stopped.append(f"LightRAG (PID: {proc.info['pid']})")
            except Exception:
                pass

    # 查找 vite 进程
    if psutil:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                if cmdline and any("vite" in str(c).lower() for c in cmdline):
                    proc.terminate()
                    stopped.append(f"Vite (PID: {proc.info['pid']})")
            except Exception:
                pass

    if stopped:
        print_success(f"已停止: {', '.join(stopped)}")
    else:
        print_info("没有发现运行中的服务")


def check_status():
    """检查服务状态"""
    print_header("服务状态检查")

    backend_running = check_service_running(BACKEND_PORT, "/health")
    frontend_running = check_service_running(FRONTEND_PORT, "/webui/")

    print(f"后端 API (端口 {BACKEND_PORT}): ", end="")
    if backend_running:
        print_color("运行中", Colors.GREEN)
        print_info(f"  └─ http://localhost:{BACKEND_PORT}/docs")
    else:
        print_color("未运行", Colors.RED)

    print(f"前端 WebUI (端口 {FRONTEND_PORT}): ", end="")
    if frontend_running:
        print_color("运行中", Colors.GREEN)
        print_info(f"  └─ http://localhost:{FRONTEND_PORT}")
    else:
        print_color("未运行", Colors.RED)

    # 检查端口占用
    print("\n端口占用情况:")
    for port in [BACKEND_PORT, FRONTEND_PORT]:
        if not check_port_available(port):
            print_color(f"  端口 {port} 已被占用", Colors.YELLOW)


def open_browser(url: str):
    """在浏览器中打开 UI"""
    print_info(f"正在浏览器中打开: {url}")
    try:
        # 延迟一下确保服务完全就绪
        time.sleep(1)
        webbrowser.open(url)
    except Exception as e:
        print_warning(f"无法自动打开浏览器: {e}")


def run_services(backend: bool = True, frontend: bool = True, open_ui: bool = True):
    """运行服务"""
    global services

    print_header("LightRAG 一键启动")

    print_info(f"项目目录: {PROJECT_ROOT}")
    print_info(f"后端端口: {BACKEND_PORT}")
    print_info(f"前端端口: {FRONTEND_PORT}")

    if backend:
        free_port(BACKEND_PORT, "Backend")
    if frontend:
        free_port(FRONTEND_PORT, "Frontend")

    # 启动后端
    backend_ready = False
    if backend:
        backend_process = start_backend()
        if backend_process:
            services.append(backend_process)
            backend_ready = True

    # 启动前端
    frontend_ready = False
    if frontend:
        frontend_process = start_frontend()
        if frontend_process:
            services.append(frontend_process)
            frontend_ready = True

    # 最终健康检测
    print_header("最终健康检测")
    check_status()

    # 打印访问信息并打开浏览器
    if services:
        print_header("服务就绪")

        target_url = None
        if backend and backend_ready:
            target_url = f"http://localhost:{BACKEND_PORT}/webui/"
            print_info(f"后端 WebUI: {target_url}")
            print_info(f"后端 API: http://localhost:{BACKEND_PORT}")
            print_info(f"API 文档:  http://localhost:{BACKEND_PORT}/docs")

        if frontend and frontend_ready:
            f_url = f"http://localhost:{FRONTEND_PORT}/webui/"
            print_info(f"前端 WebUI: {f_url}")
            if not target_url:
                target_url = f_url

        if open_ui and target_url:
            open_browser(target_url)

        print_info("\n按 Ctrl+C 停止服务\n")

        # 等待并处理输出
        try:
            while True:
                time.sleep(1)

                # 检查是否有进程退出
                for i, proc in enumerate(services):
                    if proc.poll() is not None:
                        print_error(f"服务意外退出: {proc.pid}")
                        services.pop(i)
                        break

                if not services:
                    print_error("所有服务已停止")
                    break

        except KeyboardInterrupt:
            print_warning("\n正在停止服务...")
            stop_all_services()
    else:
        print_warning("没有服务启动")


def stop_all_services():
    """停止所有启动的服务"""
    global services

    for proc in services:
        try:
            if sys.platform == "win32":
                # Windows 下使用 taskkill
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                proc.terminate()
                proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass

    services.clear()
    print_success("所有服务已停止")


# ============================================================
# 主程序
# ============================================================


def main():
    global BACKEND_HOST, BACKEND_PORT, FRONTEND_PORT
    parser = argparse.ArgumentParser(
        description="LightRAG 一键启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python start_all.py              启动所有服务（前台模式）
  python start_all.py --backend    仅启动后端
  python start_all.py --frontend   仅启动前端
  python start_all.py --check      检查服务状态
  python start_all.py --stop       停止所有服务
        """,
    )

    parser.add_argument("--host", default=BACKEND_HOST, help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--backend-port", type=int, default=BACKEND_PORT, help="后端端口（默认 9621）")
    parser.add_argument("--frontend-port", type=int, default=FRONTEND_PORT, help="前端端口（默认 5173）")

    parser.add_argument("--backend", "-b", action="store_true", help="仅启动后端服务")
    parser.add_argument("--frontend", "-f", action="store_true", help="仅启动前端服务")
    parser.add_argument("--check", "-c", action="store_true", help="检查服务状态")
    parser.add_argument("--stop", "-s", action="store_true", help="停止所有服务")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")

    args = parser.parse_args()
    BACKEND_HOST = args.host
    BACKEND_PORT = args.backend_port
    FRONTEND_PORT = args.frontend_port

    # 检查模式
    if args.check:
        check_status()
        return

    if args.stop:
        stop_services()
        return

    # 启动模式
    backend = not args.frontend
    frontend = not args.backend

    if backend and frontend:
        # 同时启动前后端
        run_services(backend=True, frontend=True, open_ui=not args.no_browser)
    elif backend:
        # 仅后端
        run_services(backend=True, frontend=False, open_ui=not args.no_browser)
    elif frontend:
        # 仅前端
        run_services(backend=False, frontend=True, open_ui=not args.no_browser)
    else:
        parser.print_help()


if __name__ == "__main__":
    # 设置信号处理
    def signal_handler(sig, frame):
        print_warning("\n\n收到停止信号，正在关闭服务...")
        stop_all_services()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    main()
