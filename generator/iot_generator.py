#!/usr/bin/env python3
import argparse
import math
import random
import sys
import time
from datetime import datetime, timedelta
import requests


def generate_value(mode: str, min_val: float, max_val: float, step_index: int = 0) -> float:
    """Generuje wartość pomiaru w zależności od wybranego trybu."""
    if mode == "random":
        return round(random.uniform(min_val, max_val), 2)
    elif mode == "sine":
        # Symulacja przebiegu sinusoidalnego mieszczącego się w zakresie min-max
        mid = (min_val + max_val) / 2
        amplitude = (max_val - min_val) / 2
        # Pełny okres co 20 kroków
        val = mid + amplitude * math.sin(2 * math.pi * step_index / 20)
        return round(val, 2)
    elif mode == "constant":
        return round((min_val + max_val) / 2, 2)
    else:
        return round(random.uniform(min_val, max_val), 2)


def send_measurement(api_url: str, api_key: str, value: float, timestamp: str = None):
    """Wysyła pojedynczy pomiar do API"""
    endpoint = f"{api_url.rstrip('/')}/api/measurements"
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "value": value
    }
    if timestamp:
        payload["timestamp"] = timestamp

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)

        if response.status_code in [200, 201]:
            print(f"[SUKCES] Wysłano wartość: {value} (Czas: {timestamp or 'bieżący'})")
        elif response.status_code == 422:
            print(
                f"[ODRZUCONO - 422] Wartość {value} spoza dopuszczalnego zakresu serii! Odpowiedź serwera: {response.text}")
        elif response.status_code == 401:
            print(f"[BŁĄD AUTORYZACI - 401] Nieprawidłowy lub wyrejestrowany klucz API! Odpowiedź: {response.text}")
        else:
            print(f"[BŁĄD {response.status_code}] Nie udało się wysłać pomiaru: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"[BŁĄD SIECI] Nie można połączyć się z API pod adresem {endpoint}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Emulator czujnika IoT")

    parser.add_argument("--url", required=True, help="Adres bazowy API (np. http://localhost:8000 lub adres wdrożenia)")
    parser.add_argument("--key", required=True,
                        help="Klucz API czujnika (uzyskany przy rejestracji czujnika w panelu administratora)")
    parser.add_argument("--mode", choices=["random", "sine", "constant"], default="random",
                        help="Sposób generowania wartości")
    parser.add_argument("--min", type=float, default=0.0, help="Minimalna dopuszczalna wartość zakresu serii")
    parser.add_argument("--max", type=float, default=100.0, help="Maksymalna dopuszczalna wartość zakresu serii")

    # Tryby pracy: historyczny (paczka wstecz) lub ciągły (live)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--history-count", type=int, help="Liczba historycznych pomiarów do wygenerowania wstecz")
    group.add_argument("--interval", type=float,
                       help="Interwał w sekundach do wysyłania pomiarów bieżących w pętli ciągłej")

    parser.add_argument("--step-seconds", type=int, default=10, help="Odstęp czasowy w sekundach między pomiarami w trybie historycznym")

    args = parser.parse_args()

    print(f"--- URUCHOMIONO GENERATOR CZUJNIKA IoT ---")
    print(f"Cel API: {args.url}")
    print(f"Tryb: {args.mode} | Zakres: [{args.min}, {args.max}]")

    if args.history_count:
        print(f"Generowanie {args.history_count} historycznych pomiarów co {args.step_seconds} sekund...")
        now = datetime.utcnow()
        for i in range(args.history_count, 0, -1):
            # Obliczanie znacznika czasu w przeszłości w sekundach
            past_time = now - timedelta(seconds=i * args.step_seconds)
            timestamp_str = past_time.isoformat() + "Z"

            val = generate_value(args.mode, args.min, args.max, step_index=i)
            send_measurement(args.url, args.key, val, timestamp=timestamp_str)

        print("Zakończono wysyłanie danych historycznych.")

    elif args.interval is not None:
        print(f"Uruchomiono ciągłe przesyłanie pomiarów co {args.interval} sekund. Naciśnij Ctrl+C, aby zatrzymać.")
        step = 0
        try:
            while True:
                val = generate_value(args.mode, args.min, args.max, step_index=step)
                send_measurement(args.url, args.key, val)
                step += 1
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nZatrzymano generator przez użytkownika.")


if __name__ == "__main__":
    main()