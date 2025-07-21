import chess
import chess.polyglot
import time
import random
from collections import defaultdict
from math import inf

# ===============================
# SmileyMate — шахматный движок
# Автор: Classic
# ===============================

# Параметры движка
MAX_ENGINE_DEPTH = 6           # Максимальная глубина поиска (больше = сильнее, но медленнее)
QUIESCENCE_DEPTH = 4           # Глубина quiescence поиска
NULL_MOVE_REDUCTION = 2        # Снижение глубины для null-move pruning

# Флаги для таблицы транспозиции
EXACT_FLAG = 0
LOWERBOUND_FLAG = 1
UPPERBOUND_FLAG = 2

# Оценка фигур (в «санти-пешках»)
piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

# Таблицы для позиционной оценки (упрощённые примеры)
pawn_mg_pst = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 27, 27, 10,  5,  5,
     0,  0,  0, 25, 25,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-25,-25, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]
king_mg_pst = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

# Собираем таблицы для фигур — пример для пешки и короля
piece_square_tables = {
    chess.PAWN: pawn_mg_pst,
    chess.KNIGHT: [0]*64,
    chess.BISHOP: [0]*64,
    chess.ROOK: [0]*64,
    chess.QUEEN: [0]*64,
    chess.KING: king_mg_pst,
}

# Инициализация вспомогательных таблиц и структур
transposition_table = {}
history_table = [[0 for _ in range(64)] for _ in range(64)]
killer_moves = defaultdict(list)
nodes_searched = 0
is_in_endgame = False

# Коэффициенты цвета для оценки
player_coefs = {True: 1, False: -1}

# Пути к книге дебютов (если есть)
PATH_TO_OPENING_BOOK = None  # можно указать путь к Polyglot книге


def evaluate_pos(board: chess.Board) -> int:
    """Оценка позиции — материал + позиционная оценка + базовая подвижность"""
    score = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece:
            val = piece_values[piece.piece_type]
            pst = piece_square_tables.get(piece.piece_type, [0]*64)
            pos_val = pst[sq if piece.color == chess.WHITE else chess.square_mirror(sq)]
            color_factor = 1 if piece.color == chess.WHITE else -1
            score += color_factor * (val + pos_val)

    # Добавим небольшую оценку подвижности
    mobility = len(list(board.legal_moves))
    score += (mobility * 10) if board.turn == chess.WHITE else -(mobility * 10)

    return score


def get_capture_score(pos: chess.Board, move: chess.Move) -> int:
    """Оценка захватов по принципу MVV-LVA (Most Valuable Victim - Least Valuable Attacker)"""
    if not pos.is_capture(move):
        return 0
    if pos.is_en_passant(move):
        return piece_values[chess.PAWN]
    victim = pos.piece_at(move.to_square)
    attacker = pos.piece_at(move.from_square)
    if victim is None or attacker is None:
        return 0
    return piece_values[victim.piece_type] - piece_values[attacker.piece_type] // 10


def get_move_score(pos: chess.Board, move: chess.Move, ply: int) -> int:
    """Функция сортировки ходов для ускорения поиска"""
    score = get_capture_score(pos, move)
    if pos.gives_check(move):
        score += 50
    if ply is not None:
        if move in killer_moves[ply]:
            score += 900
    score += history_table[move.from_square][move.to_square] // 10

    pos_hash = chess.polyglot.zobrist_hash(pos)
    tt_entry = transposition_table.get(pos_hash)
    if tt_entry is not None:
        best_move = tt_entry[1]
        if move == best_move:
            score += 2000
    return score


def sorted_legal_moves(pos: chess.Board, ply: int = None):
    """Возвращает отсортированный список ходов"""
    return sorted(list(pos.legal_moves), key=lambda m: get_move_score(pos, m, ply), reverse=True)


def quiescence(pos: chess.Board, alpha: int, beta: int, color: int, depth: int = QUIESCENCE_DEPTH) -> int:
    """Поиск в состоянии покоя (quiescence search) — предотвращение эффекта горизонта"""
    global nodes_searched
    nodes_searched += 1

    stand_pat = color * evaluate_pos(pos)
    if depth == 0:
        return stand_pat

    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in sorted_legal_moves(pos):
        if not (pos.is_capture(move) or pos.gives_check(move) or move.promotion is not None):
            continue
        pos.push(move)
        score = -quiescence(pos, -beta, -alpha, -color, depth - 1)
        pos.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def nega_max(pos: chess.Board, depth: int = MAX_ENGINE_DEPTH, alpha: int = -inf, beta: int = inf,
             color: int = +1, time_stop: float = +inf, initial_depth: int = MAX_ENGINE_DEPTH,
             ply: int = 0) -> tuple[chess.Move | None, int | str]:
    """Основной алгоритм поиска (NegaMax с альфа-бета отсечками)"""
    global nodes_searched
    nodes_searched += 1

    if pos.is_game_over():
        # Выигрыш/проигрыш/ничья
        return None, color * evaluate_pos(pos)

    if depth == 0:
        return None, quiescence(pos, alpha, beta, color)

    pos_hash = chess.polyglot.zobrist_hash(pos)
    tt_entry = transposition_table.get(pos_hash)
    if tt_entry is not None:
        tt_depth, tt_move, tt_score, tt_flag = tt_entry
        if tt_depth >= depth:
            if tt_flag == EXACT_FLAG:
                return tt_move, tt_score
            elif tt_flag == LOWERBOUND_FLAG and tt_score >= beta:
                return tt_move, tt_score
            elif tt_flag == UPPERBOUND_FLAG and tt_score <= alpha:
                return tt_move, tt_score

    original_alpha = alpha
    max_val = -inf
    best_move = None

    # Null move pruning
    if depth >= 3 and not pos.is_check() and not is_in_endgame and depth != initial_depth:
        pos.push(chess.Move.null())
        _, score = nega_max(pos, depth - 1 - NULL_MOVE_REDUCTION, -beta, -beta + 1, -color, time_stop, initial_depth, ply + 1)
        pos.pop()
        if score == "Timeout":
            return None, "Timeout"
        score = -score
        if score >= beta:
            return None, score

    moves = sorted_legal_moves(pos, ply)
    for move_index, move in enumerate(moves):
        if time.time() >= time_stop:
            return None, "Timeout"

        pos.push(move)

        # Late move reductions (LMR)
        if move_index > 3 and depth >= 3 and not pos.is_check() and not pos.is_capture(move):
            reduction = 1 if move_index < 10 else 2
            _, score = nega_max(pos, depth - 1 - reduction, -alpha - 1, -alpha, -color, time_stop, initial_depth, ply + 1)
            score = -score
            if score == "Timeout":
                pos.pop()
                return None, "Timeout"
            if score > alpha:
                _, score = nega_max(pos, depth - 1, -beta, -alpha, -color, time_stop, initial_depth, ply + 1)
                if score == "Timeout":
                    pos.pop()
                    return None, "Timeout"
                score = -score
        else:
            _, score = nega_max(pos, depth - 1, -beta, -alpha, -color, time_stop, initial_depth, ply + 1)
            if score == "Timeout":
                pos.pop()
                return None, "Timeout"
            score = -score

        pos.pop()

        if score > max_val:
            max_val = score
            best_move = move

        if score > alpha:
            alpha = score

        if alpha >= beta:
            # Update killer moves and history heuristic
            history_table[move.from_square][move.to_square] += depth * depth
            if not pos.is_capture(move):
                if move not in killer_moves[ply]:
                    if len(killer_moves[ply]) < 2:
                        killer_moves[ply].append(move)
                    else:
                        killer_moves[ply][1] = killer_moves[ply][0]
                        killer_moves[ply][0] = move
            break

    # Сохраняем в таблицу транспозиции
    if max_val <= original_alpha:
        flag = UPPERBOUND_FLAG
    elif max_val >= beta:
        flag = LOWERBOUND_FLAG
    else:
        flag = EXACT_FLAG

    # Перезаписываем только при более глубоком поиске
    if pos_hash not in transposition_table or transposition_table[pos_hash][0] <= depth:
        transposition_table[pos_hash] = (depth, best_move, max_val, flag)

    return best_move, max_val


def iterative_deepening(pos: chess.Board, max_time: float, max_depth: int = MAX_ENGINE_DEPTH, force_interrupt: bool = True) -> chess.Move | None:
    """Итеративное углубление с таймаутом"""
    global nodes_searched
    nodes_searched = 0
    start_time = time.time()
    time_stop = start_time + max_time
    best_move = None

    for depth in range(1, max_depth + 1):
        if depth > 1 and force_interrupt:
            move, score = nega_max(pos, depth, color=player_coefs[pos.turn], time_stop=time_stop, initial_depth=depth)
        else:
            move, score = nega_max(pos, depth, color=player_coefs[pos.turn], initial_depth=depth)

        if move is not None:
            best_move = move
            elapsed = time.time() - start_time
            info_str = f"info depth {depth} score cp {player_coefs[pos.turn] * score} time {int(elapsed * 1000)} nodes {nodes_searched}"
            try:
                nps = int(nodes_searched / elapsed)
                info_str += f" nps {nps}"
            except ZeroDivisionError:
                pass
            print(info_str)

        if time.time() >= time_stop:
            break

    return best_move


def in_endgame(board: chess.Board) -> bool:
    """Простая проверка эндшпиля по материалу"""
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    minor_pieces = len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.WHITE)) + \
                   len(board.pieces(chess.BISHOP, chess.BLACK)) + len(board.pieces(chess.KNIGHT, chess.BLACK))
    return queens == 0 and minor_pieces <= 1


# UCI интерфейс
def uci_loop():
    """Простой UCI интерфейс для движка SmileyMate"""
    global is_in_endgame

    print("id name SmileyMate")
    print("id author Classic")
    print("uciok")

    board = chess.Board()
    thinking = False
    max_time = 1.0

    while True:
        try:
            command = input()
        except EOFError:
            break

        if command == "uci":
            print("id name SmileyMate")
            print("id author Classic")
            print("uciok")
        elif command == "isready":
            print("readyok")
        elif command.startswith("position"):
            tokens = command.split()
            if "startpos" in tokens:
                board.reset()
                if "moves" in tokens:
                    moves_index = tokens.index("moves")
                    moves_list = tokens[moves_index + 1:]
                    for move_str in moves_list:
                        board.push_uci(move_str)
            elif "fen" in tokens:
                fen_index = tokens.index("fen")
                fen = " ".join(tokens[fen_index + 1:fen_index + 7])
                board.set_fen(fen)
                if "moves" in tokens:
                    moves_index = tokens.index("moves")
                    moves_list = tokens[moves_index + 1:]
                    for move_str in moves_list:
                        board.push_uci(move_str)
            is_in_endgame = in_endgame(board)
        elif command.startswith("go"):
            thinking = True
            max_time = 1.0
            tokens = command.split()
            if "movetime" in tokens:
                idx = tokens.index("movetime")
                max_time = float(tokens[idx + 1]) / 1000.0
            elif "wtime" in tokens:
                # Можно добавить поддержку времени на партию
                pass

            best_move = iterative_deepening(board, max_time, MAX_ENGINE_DEPTH)
            if best_move is not None:
                print(f"bestmove {best_move.uci()}")
            else:
                print("bestmove 0000")
            thinking = False
        elif command == "quit":
            break


if __name__ == "__main__":
    uci_loop()
