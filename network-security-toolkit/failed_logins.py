#!/usr/bin/env python3
"""
failed_logins.py — анализатор неудачных попыток входа по SSH.

Читает журнал аутентификации (по умолчанию /var/log/auth.log),
находит строки о неудачных попытках входа по SSH и выводит
топ IP-адресов по количеству попыток.

Примеры запуска:
    python3 failed_logins.py
    python3 failed_logins.py --file /var/log/auth.log --top 20
"""
import argparse
import re
import sys
from collections import Counter

# Регулярка вытаскивает IP из строк вида:
#   Failed password for invalid user admin from 203.0.113.45 port 51234 ssh2
FAILED_RE = re.compile(r"Failed password.*?from (\d{1,3}(?:\.\d{1,3}){3})")


def parse_log(path):
    """Возвращает Counter {ip: количество неудачных попыток}."""
    counter = Counter()
    try:
        with open(path, "r", errors="ignore") as f:
            for line in f:
                match = FAILED_RE.search(line)
                if match:
                    counter[match.group(1)] += 1
    except FileNotFoundError:
        sys.exit(f"[!] Файл не найден: {path}")
    except PermissionError:
        sys.exit(f"[!] Нет прав на чтение: {path} (попробуйте sudo)")
    return counter


def main():
    parser = argparse.ArgumentParser(description="Топ IP по неудачным входам SSH")
    parser.add_argument("--file", default="/var/log/auth.log", help="путь к журналу")
    parser.add_argument("--top", type=int, default=10, help="сколько адресов показать")
    args = parser.parse_args()

    counter = parse_log(args.file)
    if not counter:
        print("Неудачных попыток входа не найдено.")
        return

    total = sum(counter.values())
    print(f"Всего неудачных попыток: {total}")
    print(f"Уникальных IP: {len(counter)}\n")
    print(f"{'IP-адрес':<18}{'Попыток':>8}")
    print("-" * 26)
    for ip, count in counter.most_common(args.top):
        print(f"{ip:<18}{count:>8}")


if __name__ == "__main__":
    main()
