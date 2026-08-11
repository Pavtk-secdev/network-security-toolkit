#!/usr/bin/env python3
"""
net_inventory.py — инвентаризация сети через ping-sweep.

Пингует все адреса в указанной подсети (CIDR) в несколько потоков
и выводит список активных хостов. Полезно для быстрой инвентаризации
локальной сети — какие адреса заняты, какие свободны.

Примеры запуска:
    python3 net_inventory.py 192.168.1.0/24
    python3 net_inventory.py 10.0.0.0/24 --workers 100 --timeout 1
"""
import argparse
import ipaddress
import platform
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


def ping(ip, timeout):
    """Возвращает str(ip), если хост отвечает на ping, иначе None."""
    # Флаги ping различаются между Windows и Linux/macOS:
    #   -n/-c — число пакетов; -w/-W — таймаут (мс в Windows, сек в Unix)
    if platform.system() == "Windows":
        count_flag, timeout_flag = "-n", "-w"
        timeout_val = str(timeout * 1000)
    else:
        count_flag, timeout_flag = "-c", "-W"
        timeout_val = str(timeout)

    try:
        result = subprocess.run(
            ["ping", count_flag, "1", timeout_flag, timeout_val, str(ip)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return str(ip) if result.returncode == 0 else None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Ping-sweep инвентаризация сети")
    parser.add_argument("network", help="подсеть в формате CIDR, напр. 192.168.1.0/24")
    parser.add_argument("--workers", type=int, default=50, help="число потоков")
    parser.add_argument("--timeout", type=int, default=1, help="таймаут ping в секундах")
    args = parser.parse_args()

    try:
        net = ipaddress.ip_network(args.network, strict=False)
    except ValueError as e:
        sys.exit(f"[!] Неверная подсеть: {e}")

    hosts = list(net.hosts())
    print(f"Сканирую {len(hosts)} адресов в {args.network} ...\n")

    alive = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda ip: ping(ip, args.timeout), hosts):
            if result:
                alive.append(result)
                print(f"  [+] {result}")

    print(f"\nАктивных хостов: {len(alive)} из {len(hosts)}")


if __name__ == "__main__":
    main()
