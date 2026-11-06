# Rodzaje skrzyżowań: nasz edytor → SUMO

Każdy węzeł w `model.py` ma pole `rodzaj`. Przy eksporcie zamieniane na atrybut
`type` węzła SUMO (`sterowanie/eksport_sumo.py`, słownik `TYP_WEZLA_SUMO`).
Test `test_typ_wezla_zgodny_z_tabela` sprawdza każdy wiersz na prawdziwym netconvert.

## Mapowanie

| W  edytorze | `Wezel.rodzaj` | Typ węzła w SUMO | Znaki w Polsce | Uwagi                                                                                                     |
|---|---|---|---|-----------------------------------------------------------------------------------------------------------|
| Brak znaków | `brak` | `right_before_left` | brak znaków albo A-5 (skrzyżowanie dróg równorzędnych) | reguła prawej ręki                                                                                        |
| Sygnalizacja świetlna | `swiatla` | `traffic_light` | sygnalizatory S-1 / S-3 | bez programu SUMO tworzy domyślny plan świateł; z programem z karty „Fazy świateł” używa naszego (uwaga 4) |
| Droga z pierwszeństwem + „ustąp pierwszeństwa” | `pierwszenstwo` | `priority` | D-1 na głównej, A-7 na podporządkowanej, A-6a–e przed skrzyżowaniem | droga główna ma `glowna=True` (uwaga 2)                                                                   |
| Droga z pierwszeństwem + STOP na podporządkowanej | `stop` | `priority_stop` | D-1 na głównej, B-20 na podporządkowanej | podporządkowani zatrzymują się zawsze; główna jak wyżej, `glowna=True`                                    |
| STOP na wszystkich wlotach | `stop_wszystkie` | `allway_stop` | B-20 na każdym wlocie | wjeżdża ten, kto pierwszy się zatrzymał (uwaga 3)                                                         |

Węzeł na końcu drogi (dochodzi do niego jedna droga) też dostaje typ z tabeli, ale nic
tam nie reguluje. Przy `--no-turnarounds` netconvert zmienia go na `dead_end`.

## Uwagi

1. **Typ zawsze podany jawnie.** Bez niego netconvert zgaduje: przy
   50 km/h wybrał `priority`, a przy 30 km/h `right_before_left`. Skrzyżowanie bez
   znaków zachowywałoby się więc różnie zależnie od prędkości.

2. **Droga główna.** `glowna=True` daje krawędzi `priority="2"`, pozostałe dostają `1`.
   SUMO uznaje za główne dwa wloty o najwyższym priorytecie. Jeśli w węźle
   `pierwszenstwo` lub `stop` nie ma dokładnie dwóch dróg głównych, eksport pokazuje
   ostrzeżenie, a SUMO wybiera główną samo (po prędkości i liczbie pasów).
   Łamany przebieg drogi z pierwszeństwem (tabliczka T-6) działa tak samo: oba
   odcinki drogi głównej muszą mieć `glowna=True`.

3. **`stop_wszystkie`: SUMO działa po amerykańsku.** `allway_stop` to amerykański
   „4-way stop”: każdy się zatrzymuje, a wjeżdża ten, kto zatrzymał się pierwszy.
   Sprawdzone w symulacji na `przyklad.skrzyzowanie_4_wloty`: auto z zachodu
   (jedzie na wschód) i auto z południa (jedzie na północ, czyli z prawej strony
   tego pierwszego).

   | Kto dojeżdża pierwszy | `stop_wszystkie` (SUMO) | `brak` (prawa ręka) |
   |---|---|---|
   | z zachodu, o 0,3 s wcześniej | wjeżdża z zachodu | wjeżdża z południa (z prawej) |
   | jednocześnie | wjeżdża z południa | wjeżdża z południa |
   | z południa, o 0,3 s wcześniej | wjeżdża z południa | wjeżdża z południa |


4. **Światła.** Gdy węzeł ma rodzaj `swiatla`, a my nie ms programu, netconvert
   tworzy domyślny plan świateł (`potok.eksportuj_z_fazami` ostrzega o tym).
   Program faz pochodzi z karty „Fazy świateł” (`sterowanie/fazy.py`) i zastępuje
   domyślny plan. SUMO przy kolidujących zielonych nie zgłasza błędu, tylko
   rozstrzyga je regułami pierwszeństwa, dlatego program sprawdzany jest przed
   eksportem. Znaki pod sygnalizatorem (na wypadek wyłączenia świateł) to na razie
   `glowna` na drogach.

## Znaki stanu świateł w SUMO, których używamy

| Znak | Znaczenie | Działanie                                                               |
|---|---|-------------------------------------------------------------------------|
| `G` | zielone z pierwszeństwem | relacja w `Faza.zielone`                                                |
| `g` | zielone, ale trzeba ustąpić | relacja w `Faza.warunkowe` (lewoskręt ustępujący jadącym z naprzeciwka) |
| `y` | żółte | 3 s po każdej fazie                                                     |
| `r` | czerwone | —                                                                       |
| `u` | czerwone z żółtym | przed zielonym (polska sekwencja), domyślnie 1 s                        |

