import berserk
import requests
import time
import random

# ==== НАСТРОЙКИ ====
API_TOKEN = "lip_jye4gOUEzRM0VPGiBwHp"
USERNAME = "Newchessengine-ai"
OPPONENT = "maia1"
MAX_GAMES = 5
CHECK_INTERVAL = 10  # секунд между проверками

# Список тайм-контролей (в секундах)
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

# ==== ИНИЦИАЛИЗАЦИЯ ====
session = berserk.TokenSession(API_TOKEN)
client = berserk.Client(session=session)

# ==== ФУНКЦИИ ====

def get_active_game_count():
    url = f"https://lichess.org/api/games/user/{USERNAME}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/x-ndjson"  # запрос JSON-потока
    }
    params = {
        "max": 50,
        "ongoing": "true"
    }
    try:
        response = requests.get(url, headers=headers, params=params, stream=True)
        response.raise_for_status()

        count = 0
        import json
        for line in response.iter_lines():
            if not line:
                continue
            try:
                game_data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if game_data.get("status") == "started":
                count += 1

        print(f"[INFO] Найдено активных игр: {count}")
        return count

    except Exception as e:
        print(f"[ERROR] Не удалось получить список игр: {e}")
        return 0



def challenge_maia():
    """Кидает вызов @maia1 с рандомным контролем времени"""
    clock_limit, clock_increment = random.SystemRandom().choice(TIME_CONTROLS)
    print(f"[INFO] Отправка ВЫЗОВА @maia1 с контролем: {clock_limit // 60}+{clock_increment} (rated=True)")
    try:
        client.challenges.create(
            OPPONENT,
            rated=True,  # <-- здесь теперь True
            clock_limit=clock_limit,
            clock_increment=clock_increment,
            color="random",
            variant="standard"
        )
    except Exception as e:
        print(f"[ERROR] Ошибка при вызове: {e}")

# ==== ОСНОВНОЙ ЦИКЛ ====

def main():
    while True:
        active_games = get_active_game_count()
        if active_games < MAX_GAMES:
            challenge_maia()
        else:
            print(f"[INFO] У бота уже {active_games} игр. Ждём...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
