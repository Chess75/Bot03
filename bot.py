import os
import time
import random
import requests
import json
import berserk

# ==== Настройки через переменные окружения ====
API_TOKEN = os.getenv("TOKEN") or os.getenv("LICHESS_TOKEN")
USERNAME = os.getenv("LICHESS_USERNAME", "Newchessengine-ai")
OPPONENT = os.getenv("LICHESS_OPPONENT", "maia1")
MAX_GAMES = int(os.getenv("MAX_GAMES", 3))
RATED = os.getenv("RATED", "false").lower() == "true"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 10))

# ==== Тайм-контроли (секунды) ====
TIME_CONTROLS = [
    (1800, 0),   # 30+0
    (1800, 30),  # 30+30
    (900, 0),    # 15+0
    (600, 0),    # 10+0
    (600, 5),    # 10+5
    (300, 0),    # 5+0
    (300, 3),    # 5+3
    (180, 0),    # 3+0
    (180, 2),    # 3+2
    (60, 0),     # 1+0
    (60, 1),     # 1+1
    (120, 1)     # 2+1
]

# ==== Инициализация клиента berserk ====
session = berserk.TokenSession(API_TOKEN)
client = berserk.Client(session=session)

def get_active_game_count():
    """Получает количество активных игр пользователя с обработкой ошибок и лимитами"""
    url = f"https://lichess.org/api/games/user/{USERNAME}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/x-ndjson"
    }
    params = {
        "max": 50,
        "ongoing": "true"
    }

    max_attempts = 5

    for attempt in range(max_attempts):
        try:
            response = requests.get(url, headers=headers, params=params, stream=True)
            response.raise_for_status()

            count = 0
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    game_data = json.loads(line)
                    if game_data.get("status") == "started":
                        count += 1
                except json.JSONDecodeError:
                    continue

            print(f"[INFO] Активных игр найдено: {count}")
            return count

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            if status_code == 429:
                wait_time = (2 ** attempt) * 10  # экспоненциальная задержка: от 10 до ~160 секунд
                print(f"[WARNING] Получен ответ 429. Ждем {wait_time} секунд перед повтором...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] HTTP ошибка: {e}")
                break
        except Exception as e:
            print(f"[ERROR] Не удалось получить список игр: {e}")
            break

        # Если не удалось получить данные после всех попыток — возвращаем ноль.
        if attempt == max_attempts -1:
            print("[ERROR] Превышено число попыток получения данных.")
            return 0

def challenge_opponent():
    """Кидает вызов сопернику с рандомным контролем, с обработкой ошибок и повторными попытками"""
    clock_limit, clock_increment = random.SystemRandom().choice(TIME_CONTROLS)
    print(f"[INFO] Отправка вызова @{OPPONENT} {clock_limit //60}+{clock_increment} | rated={RATED}")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Перед отправкой делаем небольшую задержку
            time.sleep(1)

            client.challenges.create(
                OPPONENT,
                rated=RATED,
                clock_limit=clock_limit,
                clock_increment=clock_increment,
                color="random",
                variant="standard"
            )
            print(f"[INFO] Вызов отправлен @{OPPONENT}")
            break  # успешно, выходим из цикла

        except berserk.exceptions.HTTPError as e:
            status_code = e.status_code if hasattr(e, 'status_code') else None
            if status_code == 429:
                wait_time = (2 ** attempt) * 10  # экспоненциальная задержка
                print(f"[WARNING] Получен ответ 429. Ждем {wait_time} секунд перед повтором...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] Ошибка при отправке вызова: {e}")
                break
        except Exception as e:
            print(f"[ERROR] Не удалось отправить вызов: {e}")
            break

def main():
    while True:
        active_games = get_active_game_count()
        if active_games < MAX_GAMES:
            challenge_opponent()
        else:
            print(f"[INFO] У игрока уже {active_games} игр — ждём...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    if not API_TOKEN:
        print("[FATAL] Не задан LICHESS_TOKEN! Установи его в Secrets или переменных окружения.")
        exit(1)
    else:
        main()
