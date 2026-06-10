#!/usr/bin/env python3
"""一键启动。你只需要在终端里敲这一条:

    python3 run.py

它会自动:建环境(第一次约 1 分钟)→ 装依赖 → 问你要 API key(只问一次,存进 .env)
→ 启动服务 → 自动打开浏览器。关掉:在终端按 Ctrl+C。
"""

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
VPY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
ENV_FILE = ROOT / ".env"
PORT = int(os.environ.get("ES_PORT", "8000"))


def ensure_venv_and_deps():
    if not VPY.exists():
        print("🌱 第一次运行:正在准备环境(只需要这一次,大约 1 分钟)…")
        import venv

        venv.create(VENV, with_pip=True)
    check = subprocess.run(
        [str(VPY), "-c", "import fastapi, uvicorn, anthropic"],
        capture_output=True,
    )
    if check.returncode != 0:
        print("📦 正在安装依赖…")
        subprocess.check_call(
            [str(VPY), "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")]
        )


def load_env():
    """读 .env;没有 key 就问一次并存下来,以后不再问。"""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print()
        print("还差一样东西:Anthropic API key(在 console.anthropic.com 创建)。")
        key = input("把 key 粘贴到这里然后回车: ").strip()
        if not key:
            print("没有 key 跑不了,下次再来。")
            sys.exit(1)
        with ENV_FILE.open("a", encoding="utf-8") as f:
            f.write(f"\nANTHROPIC_API_KEY={key}\n")
        os.environ["ANTHROPIC_API_KEY"] = key
        print("✓ 已保存到 .env,以后不会再问。")


def main():
    if "--serve" not in sys.argv:
        # 第一段:在系统 python 里准备好环境,然后切进 venv 重跑自己
        ensure_venv_and_deps()
        os.chdir(ROOT)
        sys.exit(subprocess.call([str(VPY), __file__, "--serve"]))

    # 第二段:已在 venv 里
    load_env()
    url = f"http://127.0.0.1:{PORT}"
    threading.Timer(1.5, webbrowser.open, args=[url]).start()
    print()
    print(f"🌳 启动完成 → {url}  (如果浏览器没自动打开,手动点这个地址)")
    print("   关掉:在这个窗口按 Ctrl+C")
    print()
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT)


if __name__ == "__main__":
    main()
