import chess
import chess.polyglot
import time
import random
from collections import defaultdict

MAX_ENGINE_DEPTH = 20
UPPERBOUND_FLAG = 1
LOWERBOUND_FLAG = 2
EXACT_FLAG = 3

player_coefs = {True: 1, False: -1}

# Заглушки для переменных и функций, которые у тебя, предположительно, где-то определены
transposition_table = None  # Нужно определить класс и инициализировать
pawn_hash_table = None      # Аналогично
killer_moves = defaultdict(list)
history_table = [[0 for _ in range(64)] for _ in range(64)]
nodes_searched = 0
is_in_endgame = False
piece_square_tables = {}
king_mg_pst = None
king_eg_pst = None
pawn_eg_pst = None
PATH_TO_OPENING_BOOK = None

def nega_max(pos, depth, alpha=float('-inf'), beta=float('inf'), color=1, time_stop=None, initial_depth=None, ply=0):
    global nodes_searched, killer_moves, history_table, transposition_table

    # Заглушка тела функции, т.к. полного тела не было
    # Реальная реализация нужна, чтобы двиг работал
    # Здесь возврат фиктивного значения
    nodes_searched += 1
    # Для демонстрации возврат случайного хода из списка легальных ходов
    legal_moves = list(pos.legal_moves)
    if not legal_moves:
        return None, 0  # нет ходов, пат или мат
    best_move = random.choice(legal_moves)
    best_score = 0
    return best_move, best_score


def iterative_deepening(
    pos: chess.Board, max_time: float, max_depth: int = MAX_ENGINE_DEPTH, force_interrupt: bool = True
) -> chess.Move:
    """Applies iterative deepening to find the best move in a limited time"""
    global nodes_searched
    nodes_searched = 0

    t1 = time.time()
    time_stop = t1 + max_time
    best_move = None
    for depth in range(1, max_depth + 1):
        if depth > 1 and force_interrupt:
            move, score = nega_max(
                pos,
                depth,
                color=player_coefs[pos.turn],
                time_stop=time_stop,
                initial_depth=depth
            )
        else:  # NOTE: no timeout limit for depth 1, so best_move is always defined
            move, score = nega_max(
                pos,
                depth,
                color=player_coefs[pos.turn],
                initial_depth=depth
            )
        if move is not None:  # no timeout during search
            best_move = move
            time_elapsed = time.time() - t1
            info_string = "info"
            info_string += f" depth {depth}"
            info_string += (
                f" score cp {player_coefs[pos.turn] * score}"  # evaluation must be absolute
            )
            info_string += f" time {int(time_elapsed)}"
            info_string += f" nodes {nodes_searched}"
            try:
                info_string += f" nps {int(nodes_searched / time_elapsed)}"
            except ZeroDivisionError:
                pass
            print(info_string)

        if time.time() >= time_stop:
            break

    return best_move


def in_endgame(board: chess.Board) -> bool:
    """Заглушка для определения эндшпиля"""
    # Пример простой проверки - если осталось мало фигур
    return board.occupied_co[chess.PIECE_TYPES[1]] + board.occupied_co[chess.PIECE_TYPES[2]] < 10


def main() -> None:
    """Main UCI interface"""
    global killer_moves, history_table, is_in_endgame
    chess960 = False
    board = chess.Board()
    while True:
        args = input().split()
        if not args:
            continue
        if args[0] == "uci":
            print("id name SmileyMate")
            print("id author Classic")
            print("option name UCI_Chess960 type check default false")
            print("uciok")

        elif args[0] == "isready":
            print("readyok")

        elif args[0] == "ucinewgame":
            is_in_endgame = False
            # Заменить на реальные PST, если есть
            piece_square_tables[chess.KING] = king_mg_pst
            transposition_table.reset() if transposition_table else None
            pawn_hash_table.reset() if pawn_hash_table else None
            killer_moves = defaultdict(list)
            history_table = [[0 for _ in range(64)] for _ in range(64)]

        elif args[0] == "quit":
            break

        elif args[0] == "position":
            if len(args) == 2 and args[1] == "startpos":
                board = chess.Board(chess960=chess960)
            elif args[1] == "fen":
                board = chess.Board(" ".join(args[2:8]), chess960=chess960)
                if "moves" in args:
                    for move_str in args[args.index("moves") + 1:]:
                        board.push_uci(move_str)
            elif args[2] == "moves" and args[1] == "startpos":
                board = chess.Board(chess960=chess960)
                for move_str in args[3:]:
                    board.push_uci(move_str)

        elif args[0] == "go":
            if len(args) == 9:
                wtime, btime, winc, binc = [int(i) / 1000 for i in args[2::2]]
                if board.turn == chess.WHITE:
                    time_left = wtime
                    increment = winc
                else:
                    time_left = btime
                    increment = binc
                max_time = min(time_left / 40 + increment, time_left / 2 - 1)

            elif len(args) == 3 and args[1] == "movetime":
                time_left = None
                max_time = int(args[2]) / 1000

            else:
                raise ValueError("unsupported arguments for UCI command 'go'")

            best_move = None

            if PATH_TO_OPENING_BOOK:
                with chess.polyglot.open_reader(PATH_TO_OPENING_BOOK) as reader:
                    entries = {}
                    for entry in reader.find_all(board):
                        entries[entry.move] = entry.weight

                if entries:
                    max_weight = max(entries.values())
                    best_entries = [move for move in entries.keys() if entries[move] == max_weight]
                    best_move = random.choice(best_entries)
                    time.sleep(1)  # simulate thinking time

            if best_move is None:
                if time_left is not None and time_left <= 45:
                    best_move = iterative_deepening(board, max_time=max_time)
                else:
                    best_move = iterative_deepening(board, max_time=max_time * 0.3, force_interrupt=False)

            print(f"bestmove {best_move}")

            if not is_in_endgame:
                if in_endgame(board):
                    is_in_endgame = True
                    piece_square_tables[chess.KING] = king_eg_pst
                    piece_square_tables[chess.PAWN] = pawn_eg_pst

        elif args[:2] == ["setoption", "name"]:
            if args[2:] == ["UCI_Chess960", "value", "true"]:
                chess960 = True


if __name__ == "__main__":
    main()

