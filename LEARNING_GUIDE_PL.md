# Przewodnik po projekcie

Ten dokument ma pomóc Ci zrozumieć projekt na tyle dobrze, abyś potrafił:

- samodzielnie go uruchomić,
- wyjaśnić przepływ danych,
- wskazać, gdzie wykonywana jest walidacja,
- opowiedzieć, jak działa integracja z API,
- omówić obsługę błędów i testy,
- świadomie wprowadzić prostą zmianę.

## 1. Jaki problem rozwiązujemy?

Firma otrzymuje plik CSV z fakturami. Pracownik musiałby ręcznie sprawdzić:

- czy wszystkie wymagane informacje są obecne,
- czy numery faktur się nie powtarzają,
- czy daty i kwoty są poprawne,
- czy waluta oraz stawka VAT są obsługiwane,
- które faktury są zaległe,
- jaka jest łączna wartość faktur w PLN.

Program wykonuje te powtarzalne czynności według zawsze tych samych reguł.

## 2. Przepływ danych

```text
CSV
  -> wczytanie do pandas DataFrame
  -> normalizacja danych
  -> walidacja każdego wiersza
  -> pobranie kursów walut
  -> obliczenie VAT, brutto i wartości w PLN
  -> oznaczenie zaległych faktur
  -> podsumowania według waluty i klienta
  -> raporty Excel, CSV i JSON
```

`DataFrame` można na razie rozumieć jako tabelę w pamięci programu. Ma kolumny
i wiersze podobnie jak arkusz kalkulacyjny, ale możemy przetwarzać ją kodem.

## 3. Najważniejsze pliki

### `cli.py`

Punkt wejścia dla wersji uruchamianej z terminala. Odczytuje argumenty,
wczytuje CSV, uruchamia cały proces i zapisuje raporty.

### `app.py`

Interfejs Streamlit. Użytkownik nie musi znać terminala: wybiera dane, ustawia
datę raportu, naciska przycisk i pobiera wyniki.

### `validation.py`

Tutaj znajdują się reguły jakości danych. Każdy problem otrzymuje:

- numer wiersza,
- numer faktury,
- nazwę pola,
- krótki kod błędu,
- czytelny komunikat.

Niepoprawne wiersze nie są usuwane bez śladu. Trafiają do kolejki błędów, aby
człowiek mógł je poprawić.

### `exchange_rates.py`

Wysyła żądanie HTTPS GET do API NBP i odczytuje odpowiedź JSON. Dla każdej
waluty zapisujemy:

- kurs do PLN,
- źródło kursu,
- datę obowiązywania.

Jeżeli API nie odpowiada, program korzysta z oznaczonego kursu demonstracyjnego
i dodaje ostrzeżenie. Dzięki temu chwilowa awaria zewnętrznego systemu nie
przerywa całej prezentacji.

### `pipeline.py`

Łączy wszystkie kroki w jeden proces:

1. uruchamia walidację,
2. pobiera potrzebne kursy,
3. wykonuje obliczenia,
4. tworzy podsumowania,
5. zwraca jeden obiekt z kompletem wyników.

Najważniejsze wzory:

```text
VAT = kwota netto * stawka VAT / 100
brutto = netto + VAT
brutto PLN = brutto * kurs waluty do PLN
```

### `reporting.py`

Zamienia wynik procesu na:

- skoroszyt Excel,
- przetworzony CSV,
- raport JSON,
- listę błędów,
- dziennik wykonania.

## 4. Co to jest API?

API jest ustalonym sposobem komunikacji między programami. Nasz program
wysyła do NBP zapytanie pod odpowiedni adres. NBP odpowiada danymi JSON.

Przykładowa uproszczona odpowiedź:

```json
{
  "code": "EUR",
  "rates": [
    {
      "effectiveDate": "2026-07-29",
      "mid": 4.321
    }
  ]
}
```

Program wybiera `mid`, czyli średni kurs, i wykorzystuje go w obliczeniu.

## 5. Po co są testy?

Test jest małym programem sprawdzającym inny fragment programu. Przykładowo:

- dla 100 EUR netto i 23% VAT brutto wynosi 123 EUR,
- przy kursie 4,30 wartość powinna wynosić 528,90 PLN,
- termin 1 lipca i data raportu 30 lipca dają 29 dni zaległości.

Jeżeli przyszła zmiana przypadkowo zepsuje obliczenia, test zgłosi problem.

Uruchomienie:

```bash
python -m unittest discover -s tests -v
```

## 6. Jak uruchomić projekt?

Po zainstalowaniu zależności:

```bash
python cli.py --offline --as-of 2026-07-30 --output output/demo
```

Parametry:

- `--offline` - nie wywołuje API i używa kursów demonstracyjnych,
- `--as-of` - ustala dzień, dla którego sprawdzamy zaległości,
- `--output` - wskazuje folder wynikowy.

Interfejs internetowy:

```bash
streamlit run app.py
```

## 7. Jak opowiedzieć o projekcie na rozmowie?

Możesz powiedzieć:

> Chciałem przygotować niewielką automatyzację podobną do zadań opisanych
> w ofercie. Program pobiera dane faktur z CSV, sprawdza jakość danych,
> korzysta z API NBP do pobrania kursów walut i generuje raporty Excel,
> CSV oraz JSON. Oddzieliłem walidację, logikę obliczeń i raportowanie,
> dodałem obsługę niedostępności API oraz testy najważniejszych reguł.
> Przy projekcie korzystałem z AI jako wsparcia w nauce i analizie kodu,
> ale uruchomiłem testy i przechodzę przez każdy fragment, żeby rozumieć
> podjęte decyzje.

Nie ucz się tego tekstu słowo w słowo. Najważniejsze jest rozumienie kolejnych
kroków oraz możliwość pokazania konkretnego przykładu.

## 8. Co powinieneś umieć pokazać?

- znaleźć funkcję `run_pipeline`,
- wskazać jedną regułę walidacji,
- wyjaśnić wzór netto -> VAT -> brutto -> PLN,
- wskazać adres API NBP,
- uruchomić testy,
- dodać prosty komunikat lub nową regułę,
- wyjaśnić, dlaczego stosujemy fallback,
- powiedzieć, czego brakuje do wersji produkcyjnej.

## 9. Proponowane ćwiczenia

Wykonamy je razem, ale dobrze, aby część zmian była Twoja:

1. Dodanie stawki VAT 12% w konfiguracji.
2. Dodanie statusu `overdue` do osobnego podsumowania.
3. Zmiana kolejności kolumn w raporcie.
4. Dodanie reguły ostrzegającej o fakturze powyżej 10 000 PLN.
5. Dodanie historycznego kursu z dnia wystawienia faktury.

Po wykonaniu dwóch lub trzech takich zmian będziesz miał znacznie większą
swobodę podczas rozmowy technicznej.

