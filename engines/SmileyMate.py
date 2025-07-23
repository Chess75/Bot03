#!/usr/bin/env python3
import sys
import chess
import random
import time
from collections import defaultdict

piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

piece_square_tables = {
    chess.PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 10, 10, -20, -20, 10, 10, 5,
        5, -5, -10, 0, 0, -10, -5, 5,
        0, 0, 0, 20, 20, 0, 0, 0,
        5, 5, 10, 25, 25, 10, 5, 5,
        10, 10, 20, 30, 30, 20, 10, 10,
        50, 50, 50, 50, 50, 50, 50, 50,
        0, 0, 0, 0, 0, 0, 0, 0
    ],
    chess.KNIGHT: [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20, 0, 5, 5, 0, -20, -40,
        -30, 5, 10, 15, 15, 10, 5, -30,
        -30, 0, 15, 20, 20, 15, 0, -30,
        -30, 5, 15, 20, 20, 15, 5, -30,
        -30, 0, 10, 15, 15, 10, 0, -30,
        -40, -20, 0, 0, 0, 0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50
    ],
    chess.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -20, -10, -10, -10, -10, -10, -10, -20
    ],
    chess.ROOK: [
        0, 0, 0, 5, 5, 0, 0, 0,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        5, 10, 10, 10, 10, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0
    ],
    chess.QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20
    ],
    chess.KING: [
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        20, 20, 0, 0, 0, 0, 20, 20,
        20, 30, 10, 0, 0, 10, 30, 20
    ]
}

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]

def square_area(square, radius):
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

def is_open_file(board, file_index):
    for rank in range(8):
        square = chess.square(file_index, rank)
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN:
            return False
    return True

def is_half_open_file(board, file_index, color):
    for rank in range(8):
        square = chess.square(file_index, rank)
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN and piece.color == color:
            return False
    return True

def evaluate_pawn_structure(board, color):
    score = 0
    pawns = board.pieces(chess.PAWN, color)
    files = defaultdict(int)

    for square in pawns:
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        files[file] += 1

        # Изолированная пешка
        adjacent_files = [file - 1, file + 1]
        isolated = True
        for adj in adjacent_files:
            if 0 <= adj < 8 and board.pieces(chess.PAWN, color) & chess.BB_FILES[adj]:
                isolated = False
        if isolated:
            score -= 15

        # Связанная пешка
        for df in [-1, 1]:
            if 0 <= file + df < 8:
                diag_rank = rank - 1 if color == chess.WHITE else rank + 1
                if 0 <= diag_rank < 8:
                    diag_square = chess.square(file + df, diag_rank)
                    piece = board.piece_at(diag_square)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        score += 10

        # Слабая пешка
        defenders = board.attackers(color, square)
        attackers = board.attackers(not color, square)
        if not defenders and attackers:
            score -= 20

    for file, count in files.items():
        if count > 1:
            score -= 10 * (count - 1)  # Удвоенные пешки

    return score

def space_advantage(board, color):
    territory = 0
    for square in chess.SQUARES:
        rank = chess.square_rank(square)
        if (color == chess.WHITE and rank >= 4) or (color == chess.BLACK and rank <= 3):
            if board.attackers(color, square):
                territory += 1
    return territory * 2

def piece_connection_bonus(board, color):
    bonus = 0
    # Связь ладей и ферзей на открытых линиях
    for square in board.pieces(chess.ROOK, color) | board.pieces(chess.QUEEN, color):
        if any(board.attackers(color, sq) for sq in square_area(square, 1)):
            bonus += 5
    return bonus

def piece_mobility(board, color):
    mobility = 0
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        for square in board.pieces(piece_type, color):
            mobility += len(board.attacks(square))
    return mobility

def central_control(board, color):  
    control = 0
    for square in center_squares:
        piece = board.piece_at(square)
        if piece and piece.color == color:
            control += 12  # Фигура стоит в центре — чуть больше бонуса
        attackers = board.attackers(color, square)
        control += len(attackers) * 4  # Фигуры атакуют центр
    return control

def risky_attacks(board, color):
    penalty = 0
    enemy_color = not color
    for square in chess.SQUARES:
        attackers = board.attackers(color, square)
        defenders = board.attackers(enemy_color, square)

        for attacker_square in attackers:
            attacker = board.piece_at(attacker_square)
            if attacker is None:
                continue
            if defenders:
                # Если у атакуемого поля есть защита, но наша фигура слабее — плохо
                for defender_square in defenders:
                    defender = board.piece_at(defender_square)
                    if defender and piece_values[attacker.piece_type] > piece_values[defender.piece_type]:
                        penalty += piece_values[attacker.piece_type] // 10
    return penalty

def evaluate_material(board):
    material = 0
    for piece_type in piece_values:
        material += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
        material -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]
    return material

def evaluate(board):
    if board.is_checkmate():
        if board.turn:
            return -999999  # Выиграл черный
        else:
            return 999999   # Выиграл белый
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    material = evaluate_material(board)
    white = 1
    black = -1

    # Сложная эвристика по цвету
    color = chess.WHITE
    score = 0
    for c in [chess.WHITE, chess.BLACK]:
        factor = white if c == chess.WHITE else black
        score += factor * (
            evaluate_pawn_structure(board, c) +
            space_advantage(board, c) +
            piece_connection_bonus(board, c) +
            piece_mobility(board, c) +
            central_control(board, c) -
            risky_attacks(board, c)
        )
    return material + score

def is_safe_move(board, move):
    # Проверим, не теряется ли фигура после хода
    board.push(move)
    attackers = board.attackers(not board.turn, move.to_square)
    piece = board.piece_at(move.to_square)
    board.pop()
    if not attackers:
        return True
    if piece is None:
        return True
    # Фигура под атакой - проверяем стоит ли она больше того, что можно потерять
    min_attacker_value = min(piece_values[board.piece_at(a).piece_type] for a in attackers)
    return piece_values[piece.piece_type] >= min_attacker_value

def order_moves(board, moves):
    # Сортируем ходы по убыванию оценки, чтобы ускорить поиск
    scored_moves = []
    for move in moves:
        score = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                score += 10 * piece_values[victim.piece_type] - piece_values[attacker.piece_type]
        scored_moves.append((score, move))
    scored_moves.sort(reverse=True, key=lambda x: x[0])
    return [move for _, move in scored_moves]

def negamax(board, depth, alpha, beta, start_time, time_limit):
    if depth == 0 or board.is_game_over():
        return evaluate(board), None

    if time.time() - start_time > time_limit:
        return evaluate(board), None

    max_eval = -9999999
    best_move = None

    moves = list(board.legal_moves)
    moves = order_moves(board, moves)

    for move in moves:
        if not is_safe_move(board, move):
            continue  # Пропускаем рискованные ходы

        board.push(move)
        eval, _ = negamax(board, depth - 1, -beta, -alpha, start_time, time_limit)
        eval = -eval
        board.pop()

        if eval > max_eval:
            max_eval = eval
            best_move = move
        alpha = max(alpha, eval)
        if alpha >= beta:
            break

    return max_eval, best_move

def find_best_move(board, time_limit=1.0):
    best_move = None
    best_eval = -9999999
    start_time = time.time()

    depth = 1
    while True:
        if time.time() - start_time > time_limit:
            break
        eval, move = negamax(board, depth, -9999999, 9999999, start_time, time_limit)
        if move is not None:
            best_move = move
            best_eval = eval
        depth += 1
        if depth > 4:  # Максимальная глубина для контроля времени
            break
    return best_move

def main():
    board = chess.Board()

    while not board.is_game_over():
        if board.turn == chess.WHITE:
            # Ход белых (бот)
            move = find_best_move(board, time_limit=1.5)
            if move is None:
                move = random.choice(list(board.legal_moves))
            print(move)
            board.push(move)
        else:
            # Ход черных (игрок или случайный ход)
            move = random.choice(list(board.legal_moves))
            print(move)
            board.push(move)
        sys.stdout.flush()

if __name__ == "__main__":
    main()

