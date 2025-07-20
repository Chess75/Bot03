import os
import time
import random
import requests
import json
import berserk

# ==== Настройки через переменные окружения ====
API_TOKEN = os.getenv("TOKEN")  # Обрати внимание: используем переменную TOKEN
USERNAME = os.getenv("LICHESS_USERNAME", "Newchessengine-ai")
MAX_GAMES = int(os.getenv("MAX_GAMES", 3))
RATED = os.getenv("RATED", "false").lower() == "true"
BASE_INTERVAL = int(os.getenv("CHECK_INTERVAL", 10))

# ==== Тайм-контроли (секунды) ====
TIME_CONTROLS = [
    (1800, 0), (1800, 30), (900, 0), (600, 0), (600, 5),
    (300, 0), (300, 3), (180, 0), (180, 2),
    (60, 0), (60, 1), (120, 1)
]

# ==== Список соперников ====
OPPONENTS = ["maia1", "maia5", "maia9"]

# ==== Инициализация клиента ====
session = berserk.TokenSession(API_TOKEN)
client = berserk.Client(session=session)

def get_active_game_count():
    """Получает количество активных игр пользователя"""
    url = f"https://lichess.org/api/games/user/{USERNAME}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/x-ndjson"
    }
    params = {
        "max": 50,
        "ongoing": "true"
    }

    try:
        response = requests.get(url, headers=headers, params=params, stream=True)
        response.raise_for_status()

        count = 0
        for line in response.iter_lines():
            if line:
                try:
                    game_data = json.loads(line)
                    if game_data.get("status") == "started":
                        count += 1
                except json.JSONDecodeError:
                    continue

        print(f"[INFO] Активных игр найдено: {count}")
        return count
    except Exception as e:
        print(f"[ERROR] Не удалось получить список игр: {e}")
        return 0

def challenge_opponent():
    """Кидает вызов случайному Maia-сопернику с рандомным контролем"""
    clock_limit, clock_increment = random.SystemRandom().choice(TIME_CONTROLS)
    opponent = random.choice(OPPONENTS)
    print(f"[INFO] Отправка вызова @{opponent} {clock_limit // 60}+{clock_increment} | rated={RATED}")

    try:
        client.challenges.create(
            opponent,
            rated=RATED,
            clock_limit=clock_limit,
            clock_increment=clock_increment,
            color="random",
            variant="standard"
        )
    except berserk.exceptions.ResponseError as e:
        if e.response.status_code == 429:
            print("[WARN] 429 Too Many Requests — ждём 10 минут...")
            time.sleep(600)  # 10 минут пауза
        else:
            print(f"[ERROR] Ошибка при вызове: {e}")
    except Exception as e:
        print(f"[ERROR] Общая ошибка при вызове: {e}")

def main():
    interval = BASE_INTERVAL
    while True:
        active_games = get_active_game_count()
        if active_games < MAX_GAMES:
            challenge_opponent()
            interval = BASE_INTERVAL  # Сбросить интервал после успешной отправки
        else:
            print(f"[INFO] У игрока уже {active_games} игр — ждём...")

        time.sleep(interval)

if __name__ == "__main__":
    if not API_TOKEN:
        print("[FATAL] Не задан TOKEN! Установи его в Secrets или переменных окружения.")
    else:
        main()
