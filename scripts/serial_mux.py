#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serial_mux.py — Multiplexa /dev/ttyACM0 em duas PTYs:

  /tmp/ttyGUI   (read-only)  -> usada pelo TensorFlow_GUI_Simple.py
  /tmp/ttyPUTTY (read/write) -> usada pelo PuTTY para enviar comandos

Toda saída do firmware é ecoada nos dois lados; escritas vindas do PuTTY
são encaminhadas de volta para a UART real; escritas originadas do GUI
são descartadas, preservando a semântica listen-only.
"""
from __future__ import annotations

import argparse
import logging
import os
import pty
import select
import signal
import sys
import termios
import tty

try:
    import serial
except ImportError:
    sys.stderr.write("pyserial ausente. Instale: pip install pyserial\n")
    raise SystemExit(1)


def _setup_logging(debug: bool) -> logging.Logger:
    log_dir = os.environ.get("SERIAL_MUX_LOG_DIR", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        log_dir = "."
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="[%(levelname).1s] [%(asctime)s] [%(filename)s] "
               "[%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "serial_mux.log"),
                                mode="a", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    return logging.getLogger("serial_mux")


def _make_pty(link_path: str, log: logging.Logger) -> tuple[int, str]:
    """Cria PTY em modo raw e expõe via symlink estável."""
    master, slave = pty.openpty()
    slave_name = os.ttyname(slave)
    try:
        tty.setraw(master)
    except termios.error as exc:
        log.warning("raw master falhou: %s", exc)
    try:
        attrs = termios.tcgetattr(slave)
        attrs[0] = 0
        attrs[1] = 0
        attrs[3] &= ~(termios.ICANON | termios.ECHO | termios.ECHOE
                      | termios.ECHOK | termios.ECHONL | termios.ISIG)
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
    except termios.error as exc:
        log.warning("raw slave falhou: %s", exc)

    try:
        if os.path.islink(link_path) or os.path.exists(link_path):
            os.unlink(link_path)
    except OSError:
        pass
    os.symlink(slave_name, link_path)
    try:
        os.chmod(slave_name, 0o666)
    except PermissionError:
        pass
    log.info("PTY pronta link=%s slave=%s", link_path, slave_name)
    return master, slave_name


def run_mux(src: str, baud: int, link_gui: str, link_putty: str,
            log: logging.Logger) -> int:
    log.info("Iniciando mux src=%s baud=%d gui=%s putty=%s",
             src, baud, link_gui, link_putty)
    try:
        ser = serial.Serial(src, baudrate=baud, timeout=0, write_timeout=0)
    except serial.SerialException as exc:
        log.error("Falha ao abrir %s: %s", src, exc)
        return 2

    gui_m, gui_name = _make_pty(link_gui, log)
    putty_m, putty_name = _make_pty(link_putty, log)

    stop = {"flag": False}

    def _sig(signum, _f):
        log.info("Sinal %d recebido", signum)
        stop["flag"] = True

    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, _sig)

    print(f"[serial_mux] {src}@{baud}", flush=True)
    print(f"[serial_mux]   GUI   (ro) : {link_gui} -> {gui_name}", flush=True)
    print(f"[serial_mux]   PuTTY (rw) : {link_putty} -> {putty_name}",
          flush=True)

    ser_fd = ser.fileno()
    fds = [ser_fd, gui_m, putty_m]
    try:
        while not stop["flag"]:
            try:
                r, _, _ = select.select(fds, [], [], 0.5)
            except (InterruptedError, OSError):
                continue
            for fd in r:
                try:
                    data = os.read(fd, 4096)
                except OSError:
                    continue
                if not data:
                    continue
                if fd == ser_fd:
                    for w in (gui_m, putty_m):
                        try:
                            os.write(w, data)
                        except OSError:
                            pass
                elif fd == putty_m:
                    try:
                        os.write(ser_fd, data)
                    except OSError:
                        pass
                # fd == gui_m: descarta (listen-only)
    finally:
        for link in (link_gui, link_putty):
            try:
                os.unlink(link)
            except OSError:
                pass
        try:
            os.close(gui_m)
            os.close(putty_m)
        except OSError:
            pass
        try:
            ser.close()
        except serial.SerialException:
            pass
        log.info("Mux encerrado")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Mux serial ttyACM0 -> 2 PTYs")
    p.add_argument("--src", default=os.environ.get("SERIAL_MUX_SRC",
                                                   "/dev/ttyACM0"))
    p.add_argument("--baud", type=int,
                   default=int(os.environ.get("SERIAL_MUX_BAUD", "115200")))
    p.add_argument("--gui", default=os.environ.get("SERIAL_MUX_LINK_GUI",
                                                   "/tmp/ttyGUI"))
    p.add_argument("--putty", default=os.environ.get("SERIAL_MUX_LINK_PUTTY",
                                                     "/tmp/ttyPUTTY"))
    p.add_argument("--debug", action="store_true",
                   default=bool(os.environ.get("SERIAL_MUX_DEBUG")))
    args = p.parse_args(argv)
    log = _setup_logging(args.debug)
    return run_mux(args.src, args.baud, args.gui, args.putty, log)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
