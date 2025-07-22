#!/usr/bin/env python3
import sys
import chess
import random
import time
import threading
import concurrent.futures
import logging
from collections import defaultdict, namedtuple

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("SmileyMate")

# --- Константы ---
INFINITY = 1000000
MATE_SCORE = 999000
MAX_DEPTH = 6

# --- Транспозиционный стол с типами записей ---
Entry = namedtuple('Entry', ['depth', 'score', 'flag', 'best_move'])
EXACT, LOWERBOUND, UPPERBOUND = 0, 1, 2

class TranspositionTable:
    def __init__(self):
        self.table = {}
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            return self.table.get(key, None)

    def store(self, key, entry):
        with self.lock:
            existing = self.table.get(key)
            if existing is None or entry.depth >= existing.depth:
                self.table[key] = entry

    def clear(self):
        with self.lock:
            self.table.clear()

# --- Оценка фигур ---
piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# --- Полные таблицы расположения фигур (Piece-Square Tables, PST) ---

# Пешка (белая, черная зеркально)
pawn_pst = [
      0,   0,   0,   0,   0,   0,   0,   0,
     50,  50,  50,  50,  50,  50,  50,  50,
     10,  10,  20,  30,  30,  20,  10,  10,
      5,   5,  10,  27,  27,  10,   5,   5,
      0,   0,   0,  25,  25,   0,   0,   0,
      5,  -5, -10,   0,   0, -10,  -5,   5,
      5,  10,  10, -20, -20,  10,  10,   5,
      0,   0,   0,   0,   0,   0,   0,   0
]

knight_pst = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]

bishop_pst = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]

rook_pst = [
     0,   0,   5,  10,  10,   5,   0,   0,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     5,  10,  10,  10,  10,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]

queen_pst = [
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -10,   5,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   0,   5,   5,   5,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20,
]

king_middle_pst = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20,
]

king_end_pst = [
    -50, -40, -30, -20, -20, -30, -40, -50,
    -30, -20, -10,   0,   0, -10, -20, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  30,  40,  40,  30, -10, -30,
    -30, -10,  20,  30,  30,  20, -10, -30,
    -30, -30,   0,   0,   0,   0, -30, -30,
    -50, -30, -30, -30, -30, -30, -30, -50,
]

piece_square_tables = {
    chess.PAWN: pawn_pst,
    chess.KNIGHT: knight_pst,
    chess.BISHOP: bishop_pst,
    chess.ROOK: rook_pst,
    chess.QUEEN: queen_pst,
    chess.KING: king_middle_pst  # Для начала, будем менять для эндшпиля отдельно
}

# --- Центр доски ---
center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]

# --- Класс шахматного движка ---

class SmileyMateEngine:
    def __init__(self):
        self.board = chess.Board()
        self.tt = TranspositionTable()
        self.lock = threading.Lock()
        self.killer_moves = defaultdict(lambda: [None, None])  # для эвристики killer moves
        self.history_heuristic = defaultdict(int)  # для history heuristic
        self.nodes_searched = 0
        self.start_time = 0
        self.stop_search = False
        self.best_move = None

    def is_endgame(self):
        # Простая эвристика конца игры: мало ферзей, мало фигур
        queens = len(self.board.pieces(chess.QUEEN, chess.WHITE)) + len(self.board.pieces(chess.QUEEN, chess.BLACK))
        minor_major = 0
        for pt in [chess.ROOK, chess.BISHOP, chess.KNIGHT]:
            minor_major += len(self.board.pieces(pt, chess.WHITE))
            minor_major += len(self.board.pieces(pt, chess.BLACK))
        return queens == 0 or (queens <= 1 and minor_major <= 2)

    def evaluate_pawn_structure(self, color):
        score = 0
        pawns = self.board.pieces(chess.PAWN, color)
        files = [0] * 8
        for sq in pawns:
            files[chess.square_file(sq)] += 1
        for i in range(8):
            if files[i] > 1:
                score -= 10 * (files[i] - 1)  # штраф за дубль пешек
            isolated = files[i] > 0 and \
                       (i == 0 or files[i-1] == 0) and \
                       (i == 7 or files[i+1] == 0)
            if isolated:
                score -= 15  # штраф за изолированную пешку
        return score

    def evaluate_king_safety(self, color):
        king_sq = self.board.king(color)
        if king_sq is None:
            return -MATE_SCORE
        danger = -len(self.board.attackers(not color, king_sq)) * 20
        for sq in self.square_area(king_sq, 1):
            piece = self.board.piece_at(sq)
            if piece and piece.color == color:
                danger += 5
        return danger

    def square_area(self, square, radius):
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        area = []
        for df in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                f = file + df
                r = rank + dr
                if 0 <= f < 8 and 0 <= r < 8:
                    area.append(chess.square(f, r))
        return area

    def evaluate_board(self):
        # Быстрые проверки на мат/пат
        if self.board.is_checkmate():
            return -MATE_SCORE if self.board.turn else MATE_SCORE
        if self.board.is_stalemate() or self.board.is_insufficient_material():
            return 0

        score = 0
        # Материальная оценка
        for pt, val in piece_values.items():
            score += len(self.board.pieces(pt, chess.WHITE)) * val
            score -= len(self.board.pieces(pt, chess.BLACK)) * val

        # Таблицы расположения фигур
        endgame = self.is_endgame()
        for pt in piece_values.keys():
            table = piece_square_tables[pt]
            for sq in self.board.pieces(pt, chess.WHITE):
                if pt == chess.KING:
                    val = king_end_pst[sq] if endgame else king_middle_pst[sq]
                    score += val
                else:
                    score += table[sq]
            for sq in self.board.pieces(pt, chess.BLACK):
                if pt == chess.KING:
                    val = king_end_pst[chess.square_mirror(sq)] if endgame else king_middle_pst[chess.square_mirror(sq)]
                    score -= val
                else:
                    score -= table[chess.square_mirror(sq)]

        # Безопасность короля
        score += self.evaluate_king_safety(chess.WHITE)
        score -= self.evaluate_king_safety(chess.BLACK)

        # Структура пешек
        score += self.evaluate_pawn_structure(chess.WHITE)
        score -= self.evaluate_pawn_structure(chess.BLACK)

        # Контроль центра
        for sq in center_squares:
            piece = self.board.piece_at(sq)
            if piece:
                score += 10 if piece.color == chess.WHITE else -10

        # Мобильность - количество легальных ходов * 5
        mobility = len(list(self.board.legal_moves))
        score += (mobility if self.board.turn == chess.WHITE else -mobility) * 5

        return score

    # --- Quiescence search (поиск по тихим ходам) ---
    def quiescence(self, alpha, beta, color):
        stand_pat = color * self.evaluate_board()
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        for move in self.board.legal_moves:
            if not self.board.is_capture(move):
                continue
            self.board.push(move)
            score = -self.quiescence(-beta, -alpha, -color)
            self.board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    # --- Negamax с альфа-бета отсечками и транзпозиционным столом ---
    def negamax(self, depth, alpha, beta, color, ply=0):
        self.nodes_searched += 1
        if self.stop_search:
            return 0

        # Проверка в таблице транзиций
        key = self.board.transposition_key()
        tt_entry = self.tt.get(key)
        if tt_entry and tt_entry.depth >= depth:
            if tt_entry.flag == EXACT:
                return tt_entry.score
            elif tt_entry.flag == LOWERBOUND:
                alpha = max(alpha, tt_entry.score)
            elif tt_entry.flag == UPPERBOUND:
                beta = min(beta, tt_entry.score)
            if alpha >= beta:
                return tt_entry.score

        if depth == 0:
            return self.quiescence(alpha, beta, color)

        max_eval = -INFINITY
        best_move = None

        legal_moves = list(self.board.legal_moves)
        legal_moves = self.order_moves(legal_moves, ply)

        for move in legal_moves:
            self.board.push(move)
            score = -self.negamax(depth - 1, -beta, -alpha, -color, ply + 1)
            self.board.pop()

            if score > max_eval:
                max_eval = score
                best_move = move
            if score > alpha:
                alpha = score
                # Обновляем эвристики
                self.history_heuristic[(self.board.turn, move.from_square, move.to_square)] += depth * depth
            if alpha >= beta:
                # Killer move heuristic
                if move not in self.killer_moves[ply]:
                    self.killer_moves[ply][1] = self.killer_moves[ply][0]
                    self.killer_moves[ply][0] = move
                break

        # Сохраняем в таблицу транзиций
        flag = EXACT
        if max_eval <= alpha:
            flag = UPPERBOUND
        elif max_eval >= beta:
            flag = LOWERBOUND
        self.tt.store(key, Entry(depth, max_eval, flag, best_move))

        if ply == 0:
            self.best_move = best_move

        return max_eval

    # --- Упорядочивание ходов ---
    def order_moves(self, moves, ply):
        tt_entry = self.tt.get(self.board.transposition_key())
        if tt_entry and tt_entry.best_move in moves:
            moves.remove(tt_entry.best_move)
            moves.insert(0, tt_entry.best_move)

        for killer in self.killer_moves[ply]:
            if killer and killer in moves:
                if killer in moves:
                    moves.remove(killer)
                moves.insert(1, killer)

        moves.sort(key=lambda m: self.history_heuristic.get((self.board.turn, m.from_square, m.to_square), 0), reverse=True)
        return moves

    # --- Итеративное углубление ---
    def iterative_deepening(self, max_depth, max_time):
        self.start_time = time.time()
        self.stop_search = False
        self.nodes_searched = 0
        best_move = None
        for depth in range(1, max_depth + 1):
            score = self.negamax(depth, -INFINITY, INFINITY, 1 if self.board.turn == chess.WHITE else -1)
            logger.info(f"Depth: {depth} Score: {score} Nodes: {self.nodes_searched}")
            if self.stop_search:
                break
            best_move = self.best_move
            if time.time() - self.start_time > max_time:
                logger.info("Time limit reached.")
                break
        return best_move

    def play(self, max_depth=6, max_time=3.0):
        move = self.iterative_deepening(max_depth, max_time)
        if move:
            self.board.push(move)
            logger.info(f"Engine plays move: {move.uci()}")
        else:
            logger.info("No legal moves found.")
        return move

    # --- UCI интерфейс ---

    def uci_loop(self):
        logger.info("SmileyMate engine ready (UCI mode)")
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "quit":
                break
            elif line.startswith("position"):
                self.handle_position(line)
            elif line.startswith("go"):
                self.handle_go(line)
            elif line == "isready":
                print("readyok")
            elif line == "ucinewgame":
                self.board.reset()
                self.tt.clear()
                self.killer_moves.clear()
                self.history_heuristic.clear()
            elif line == "d":
                print(self.board)
            else:
                print(f"Unknown command: {line}")

    def handle_position(self, cmd):
        tokens = cmd.split()
        idx = tokens.index("moves") if "moves" in tokens else -1
        if idx == -1:
            self.board.reset()
        else:
            self.board.reset()
            for move_str in tokens[idx + 1:]:
                move = chess.Move.from_uci(move_str)
                self.board.push(move)

    def handle_go(self, cmd):
        max_time = 3.0
        max_depth = 6
        tokens = cmd.split()
        if "movetime" in tokens:
            mt_idx = tokens.index("movetime")
            max_time = float(tokens[mt_idx + 1]) / 1000.0
        if "depth" in tokens:
            d_idx = tokens.index("depth")
            max_depth = int(tokens[d_idx + 1])
        best_move = self.iterative_deepening(max_depth, max_time)
        if best_move:
            print(f"bestmove {best_move.uci()}")
        else:
            print("bestmove 0000")

if __name__ == "__main__":
    engine = SmileyMateEngine()
    engine.uci_loop()
