#!/usr/bin/env python3
"""
ip_enrich.py — обогащение IP-адресов гео- и репутационными данными.

Для каждого IP запрашивает:
  - геолокацию и провайдера через ip-api.com (бесплатно, без ключа);
  - оценку репутации через AbuseIPDB (нужен бесплатный API-ключ,
    передаётся через переменную окружения ABUSEIPDB_KEY).
Результаты выводятся таблицей и по желанию сохраняются в SQLite.

Примеры запуска:
    python3 ip_enrich.py --ips 8.8.8.8 1.1.1.1
    python3 ip_enrich.py --file ips.txt --db results.db
    ABUSEIPDB_KEY=xxxx python3 ip_enrich.py --file ips.txt --db results.db
"""
import argparse
import os
import sqlite3
import sys
import time

import requests

IPAPI_URL = "http://ip-api.com/json/{}"
ABUSE_URL = "https://api.abuseipdb.com/api/v2/check"


def read_ips(args):
    """Собирает список IP из аргументов --ips и/или файла --file."""
    ips = list(args.ips or [])
    if args.file:
        try:
            with open(args.file) as f:
                ips += [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            sys.exit(f"[!] Файл не найден: {args.file}")
    return ips


def geo_lookup(ip):
    """Геолокация и провайдер через ip-api.com."""
    try:
        r = requests.get(IPAPI_URL.format(ip), timeout=10)
        data = r.json()
        if data.get("status") == "success":
            return {
                "country": data.get("country", "-"),
                "city": data.get("city", "-"),
                "isp": data.get("isp", "-"),
            }
    except requests.RequestException as e:
        print(f"[!] Ошибка запроса для {ip}: {e}", file=sys.stderr)
    return {"country": "-", "city": "-", "isp": "-"}


def abuse_lookup(ip, key):
    """Оценка репутации (0-100) через AbuseIPDB, если задан ключ."""
    if not key:
        return None
    try:
        r = requests.get(
            ABUSE_URL,
            headers={"Key": key, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90},
            timeout=10,
        )
        return r.json().get("data", {}).get("abuseConfidenceScore")
    except requests.RequestException as e:
        print(f"[!] AbuseIPDB ошибка для {ip}: {e}", file=sys.stderr)
        return None


def save_db(path, rows):
    """Сохраняет результаты в SQLite-таблицу enrichment."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS enrichment (
               ip TEXT PRIMARY KEY,
               country TEXT,
               city TEXT,
               isp TEXT,
               abuse_score INTEGER,
               checked_at TEXT
           )"""
    )
    conn.executemany(
        """INSERT OR REPLACE INTO enrichment
           VALUES (:ip, :country, :city, :isp, :abuse_score, :checked_at)""",
        rows,
    )
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Обогащение IP гео и репутацией")
    parser.add_argument("--ips", nargs="*", help="IP-адреса через пробел")
    parser.add_argument("--file", help="файл со списком IP (по одному на строку)")
    parser.add_argument("--db", help="сохранить результаты в SQLite-файл")
    args = parser.parse_args()

    ips = read_ips(args)
    if not ips:
        sys.exit("[!] Укажите IP через --ips или --file")

    key = os.environ.get("ABUSEIPDB_KEY")
    rows = []
    print(f"{'IP':<16}{'Страна':<16}{'Провайдер':<28}{'Abuse':>6}")
    print("-" * 66)
    for ip in ips:
        geo = geo_lookup(ip)
        score = abuse_lookup(ip, key)
        score_str = "-" if score is None else str(score)
        print(f"{ip:<16}{geo['country']:<16}{geo['isp'][:26]:<28}{score_str:>6}")
        rows.append({
            "ip": ip,
            **geo,
            "abuse_score": score,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        time.sleep(1.5)  # уважаем лимиты бесплатных API

    if args.db:
        save_db(args.db, rows)
        print(f"\nСохранено в {args.db}")


if __name__ == "__main__":
    main()
