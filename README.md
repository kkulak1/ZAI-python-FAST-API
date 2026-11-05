# ZAI – API i generator pomiarów IoT

Projekt udostępnia API do zarządzania seriami pomiarowymi, czujnikami i
pomiarami. Katalog `generator` zawiera emulator czujnika IoT, który generuje
wartości i wysyła je do endpointu `POST /api/measurements`.

## Jak działa generator

Generator:

1. pobiera adres API oraz klucz API konkretnego czujnika z argumentów
   uruchomieniowych,
2. generuje wartość w wybranym trybie,
3. wysyła żądanie `POST /api/measurements` z nagłówkami:
   - `X-API-Key` – klucz przypisany do czujnika,
   - `Content-Type: application/json`,
4. wyświetla wynik żądania w terminalu.

Treść wysyłanego żądania zawiera `value` oraz opcjonalnie `timestamp`.
`series_id` nie jest przekazywane przez generator. API wyszukuje czujnik na
podstawie klucza API i przypisuje pomiar do serii powiązanej z tym czujnikiem.

Generator obsługuje dwa tryby pracy:

- **historyczny** – wysyła określoną liczbę pomiarów ze znacznikami czasu
  cofniętymi względem chwili uruchomienia,
- **ciągły** – wysyła jeden pomiar co określony interwał aż do zatrzymania
  kombinacją `Ctrl+C`.

## Wymagania

- Python 3.10 lub nowszy,
- uruchomione API,
- zainstalowana biblioteka `requests`,
- zarejestrowany czujnik z kluczem API.

Instalacja biblioteki w aktywnym środowisku wirtualnym:

```powershell
python -m pip install requests
```

## Przygotowanie czujnika

Klucz API jest generowany podczas rejestracji czujnika. Rejestracja wymaga
tokenu administratora uzyskanego przez `POST /api/auth/login`.

Przykładowe logowanie:

```powershell
curl.exe -X POST http://localhost:8000/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"username\":\"admin\",\"password\":\"HASLO_ADMINA\"}'
```

Następnie należy użyć tokenu w nagłówku `Authorization` podczas rejestracji
czujnika. Wartość `seriesId` musi wskazywać istniejącą serię:

```powershell
curl.exe -X POST http://localhost:8000/api/sensors `
  -H "Authorization: Bearer TOKEN_ADMINA" `
  -H "Content-Type: application/json" `
  -d '{\"name\":\"Czujnik salonu\",\"seriesId\":1}'
```

Odpowiedź rejestracji zawiera `apiKey`. Jest to jedyny moment, w którym klucz
jest zwracany przez API, dlatego należy zapisać go w bezpiecznym miejscu.
W bazie przechowywany jest wyłącznie skrót klucza.

## Uruchamianie generatora

Polecenia należy wykonywać z katalogu głównego projektu.

### Tryb ciągły

Wysyłanie pomiaru co 10 sekund z wartościami losowymi:

```powershell
python .\generator\iot_generator.py `
  --url http://localhost:8000 `
  --key KLUCZ_API_CZUJNIKA `
  --mode random `
  --min 0 `
  --max 100 `
  --interval 10
```

Zatrzymanie generatora:

```text
Ctrl+C
```

### Tryb historyczny

Wysłanie 20 pomiarów historycznych co 60 sekund:

```powershell
python .\generator\iot_generator.py `
  --url http://localhost:8000 `
  --key KLUCZ_API_CZUJNIKA `
  --mode sine `
  --min 0 `
  --max 100 `
  --history-count 20 `
  --step-seconds 60
```

Tryb historyczny tworzy znaczniki czasu w przeszłości, od najstarszego do
najnowszego pomiaru. Domyślna wartość `--step-seconds` wynosi 10.

## Tryby generowania wartości

Argument `--mode` przyjmuje następujące wartości:

| Tryb | Działanie |
|---|---|
| `random` | Losuje wartość z przedziału `--min`–`--max`. |
| `sine` | Generuje przebieg sinusoidalny w podanym przedziale; pełny okres trwa 20 kroków. |
| `constant` | Wysyła średnią wartość przedziału. |

Zakres `--min` i `--max` powinien odpowiadać zakresowi serii przypisanej do
czujnika. Wartości spoza zakresu są odrzucane przez API kodem `422`.

## Parametry generatora

| Parametr | Wymagany | Opis |
|---|---:|---|
| `--url` | tak | Bazowy adres API, np. `http://localhost:8000`. |
| `--key` | tak | Klucz API zarejestrowanego czujnika. |
| `--mode` | nie | `random`, `sine` albo `constant`; domyślnie `random`. |
| `--min` | nie | Minimalna generowana wartość; domyślnie `0`. |
| `--max` | nie | Maksymalna generowana wartość; domyślnie `100`. |
| `--history-count` | jeden z trybów pracy | Liczba pomiarów historycznych do wysłania. |
| `--interval` | jeden z trybów pracy | Odstęp w sekundach między pomiarami ciągłymi. |
| `--step-seconds` | nie | Odstęp między znacznikami czasu w trybie historycznym; domyślnie `10`. |

`--history-count` i `--interval` wzajemnie się wykluczają, ale jeden z nich
jest wymagany.

## Diagnostyka błędów

Generator wypisuje odpowiedź API dla błędów. Najczęstsze przypadki:

- `401` – klucz API jest nieprawidłowy, wygasł lub czujnik został usunięty,
- `422` – wartość nie mieści się w zakresie serii albo dane wejściowe są
  niepoprawne,
- `415` – żądanie nie ma `Content-Type: application/json`,
- błąd sieci – API jest niedostępne albo podano nieprawidłowy adres w `--url`.

Dla wdrożenia korzystającego z HTTPS należy podać adres zaczynający się od
`https://`, na przykład:

```powershell
python .\generator\iot_generator.py `
  --url https://api.example.com `
  --key KLUCZ_API_CZUJNIKA `
  --mode constant `
  --interval 30
```

## Odczyt zapisanych pomiarów

Wszystkie pomiary można pobrać pod endpointem: '/api/measurements'.

