import os
import time
import random
import requests
import json
import berserk

# ==== Настройки через переменные окружения ====
API_TOKEN = os.getenv("LICHESS_TOKEN")
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
    except Exception as e:
        print(f"[ERROR] Не удалось получить список игр: {e}")
        return 0

def challenge_opponent():
    """Кидает вызов сопернику с рандомным контролем"""
    clock_limit, clock_increment = random.SystemRandom().choice(TIME_CONTROLS)
    print(f"[INFO] Отправка вызова @{OPPONENT} {clock_limit // 60}+{clock_increment} | rated={RATED}")

    try:
        client.challenges.create(
            OPPONENT,
            rated=RATED,
            clock_limit=clock_limit,
            clock_increment=clock_increment,
            color="random",
            variant="standard"
        )
    except Exception as e:
        print(f"[ERROR] Ошибка при отправке вызова: {e}")

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
    else:
        main()
