#!/usr/bin/env python3
"""Install Tiny11 into a qcow2 using QEMU/KVM and unattended setup."""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kwargs)


def monitor_command(sock_path: Path, command: str) -> str:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(3)
            s.connect(str(sock_path))
            s.recv(4096)
            s.sendall((command + "\n").encode())
            time.sleep(0.15)
            return s.recv(4096).decode(errors="replace")
    except OSError as exc:
        return repr(exc)


def rdp_handshake() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 3389), timeout=3) as s:
            s.settimeout(3)
            return s.recv(4).startswith(b"\x03\x00")
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--autounattend", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=5400)
    args = parser.parse_args()

    args.workdir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    floppy = args.workdir / "autounattend.img"
    monitor = args.workdir / "qemu-monitor.sock"
    serial = args.workdir / "serial.log"
    stderr = args.workdir / "qemu.stderr.log"
    screen = args.workdir / "screen.ppm"

    for p in (args.output, floppy, monitor, serial, stderr, screen):
        if p.exists():
            p.unlink()

    run(["qemu-img", "create", "-f", "qcow2", str(args.output), "32G"], stdout=subprocess.DEVNULL)
    run(["qemu-img", "create", "-f", "raw", str(floppy), "1.44M"], stdout=subprocess.DEVNULL)
    run(["mkfs.fat", "-F", "12", str(floppy)], stdout=subprocess.DEVNULL)
    run(["mcopy", "-i", str(floppy), str(args.autounattend), "::/Autounattend.xml"])

    qemu = [
        "qemu-system-x86_64",
        "-accel", "kvm",
        "-machine", "pc",
        "-cpu", "qemu64",
        "-m", "4G",
        "-smp", "2",
        "-drive", f"file={args.output},if=ide,format=qcow2",
        "-cdrom", str(args.iso),
        "-drive", f"file={floppy},if=floppy,format=raw",
        "-boot", "menu=off,once=d",
        "-netdev", "user,id=net0,hostfwd=tcp:127.0.0.1:3389-:3389",
        "-device", "e1000,netdev=net0",
        "-vga", "std",
        "-display", "none",
        "-serial", f"file:{serial}",
        "-monitor", f"unix:{monitor},server=on,wait=off",
    ]

    with stderr.open("ab") as err:
        proc = subprocess.Popen(qemu, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err, start_new_session=True)

    start = time.time()
    try:
        time.sleep(8)
        # The Tiny11 BIOS boot sector may ask for a keypress before loading setup.
        for _ in range(5):
            monitor_command(monitor, "sendkey spc")
            if proc.poll() is not None:
                break
            time.sleep(2)

        last_screen = 0.0
        while proc.poll() is None:
            elapsed = int(time.time() - start)
            if elapsed > args.timeout:
                raise TimeoutError(f"Windows image build exceeded {args.timeout} seconds")
            if time.time() - last_screen >= 30:
                monitor_command(monitor, f"screendump {screen}")
                last_screen = time.time()
            disk_bytes = args.output.stat().st_size if args.output.exists() else 0
            serial_bytes = serial.stat().st_size if serial.exists() else 0
            print(
                f"heartbeat elapsed={elapsed}s disk_bytes={disk_bytes} "
                f"serial_bytes={serial_bytes} rdp_handshake={rdp_handshake()}",
                flush=True,
            )
            if rdp_handshake():
                print("RDP handshake detected; Windows image is ready.", flush=True)
                time.sleep(15)
                break
            time.sleep(15)

        if proc.poll() is not None:
            tail = stderr.read_text(errors="replace")[-4000:]
            raise RuntimeError(f"QEMU exited with code {proc.returncode}\n{tail}")

        run(["qemu-img", "check", str(args.output)])
        print("Preinstalled qcow2 created:", args.output, flush=True)
        return 0
    finally:
        if proc.poll() is None:
            monitor_command(monitor, "quit")
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=15)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr, flush=True)
        raise
