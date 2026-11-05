# Licznik jazdy - Zadanie 1

Pakiet z instrukcji: prędkość na żywo, podsumowanie co sekundę oraz okno PyQt5.
Dystans i czas autonomiczny są obliczane między wiadomościami prędkości,
z zegara węzła. Tryb używa RELIABLE / TRANSIENT_LOCAL.
Okno odczytuje spójną kopię stanu i zatrzymuje executor przed zniszczeniem węzła.

## Budowanie i uruchamianie

Uruchom CARLA i Autoware zgodnie z głównym README. Na hoście:

```bash
./scripts/aw_shell.sh
```

W kontenerze:

```bash
cd ~/ws
rosdep install --from-paths src/licznik_jazdy --ignore-src -r -y
colcon build --symlink-install --packages-select licznik_jazdy
source install/setup.bash
ros2 run licznik_jazdy predkosc --ros-args -p use_sim_time:=true
ros2 run licznik_jazdy licznik --ros-args -p use_sim_time:=true
ros2 run licznik_jazdy okno --ros-args -p use_sim_time:=true
```

Komendy ros2 run uruchamiaj osobno (Ctrl+C kończy bieżącą).
Do równoczesnego logu i okna użyj dwóch terminali.
Nie uruchamiaj dwóch kopii o tej samej nazwie węzła.
Druga kopia wymaga np. `-r __node:=licznik_2`.

## Sprawdzenie w symulacji

- Sprawdź typy i QoS przez ros2 topic info -v oraz ros2 interface show.
- Prędkość powinna odpowiadać wiadomości longitudinal_velocity razy 3.6.
- Tryb powinien być widoczny zaraz po starcie dzięki API_QOS.
- Przejedź znany odcinek i porównaj dystans; czas autonomiczny rośnie w AUTONOMOUS.
- Porównaj okno i log; zamknij okno krzyżykiem oraz Ctrl+C.
- Przy cofnięciu zegara licznik nie odejmuje drogi ani czasu.

Częstotliwość publikacji i zachowanie po dojeździe należy sprawdzić
w uruchomionej symulacji; nie są wynikami pomiaru tego pakietu.
Przy błędzie wyświetlacza sprawdź konfigurację X11 z głównego README.

Zakres obejmuje kroki tutorialu Zad 1. Końcowe porównanie z projektem 1
nie zawiera pełnej specyfikacji sześciu tematów i nie jest implementowane.
