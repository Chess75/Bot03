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
                diag_square = chess.square(file + df, rank - 1 if color == chess.WHITE else rank + 1)
                if board.piece_at(diag_square) and board.piece_at(diag_square).piece_type == chess.PAWN and board.piece_at(diag_square).color == color:
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
    pieces = board.pieces(chess.ROOK, color) | board.pieces(chess.QUEEN, color)
    for square in pieces:
        if board.attackers(color, square):
            bonus += 5
    return bonus

def piece_mobility(board, color):
    mobility = 0
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        for square in board.pieces(piece_type, color):
            mobility += len(board.attacks(square))
    return mobility

def evaluate_board(board):
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    for piece_type in piece_values:
        white_pieces = board.pieces(piece_type, chess.WHITE)
        black_pieces = board.pieces(piece_type, chess.BLACK)
        score += len(white_pieces) * piece_values[piece_type]
        score -= len(black_pieces) * piece_values[piece_type]

    for piece_type, table in piece_square_tables.items():
        for square in board.pieces(piece_type, chess.WHITE):
            score += table[square]
        for square in board.pieces(piece_type, chess.BLACK):
            score -= table[chess.square_mirror(square)]

    def king_safety(color):
        king_square = board.king(color)
        if king_square is None:
            return -9999
        danger = 0
        attackers = board.attackers(not color, king_square)
        danger -= len(attackers) * 20
        for square in square_area(king_square, 1):
            piece = board.piece_at(square)
            if piece and piece.color == color:
                danger += 5
        return danger

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

    score += len(list(board.legal_moves)) * (1 if board.turn == chess.WHITE else -1)

    for color in [chess.WHITE, chess.BLACK]:
        sign = 1 if color == chess.WHITE else -1

        # Ладья/ферзь на открытой линии
        for rook in board.pieces(chess.ROOK, color):
            file = chess.square_file(rook)
            if is_open_file(board, file):
                score += 30 * sign
            elif is_half_open_file(board, file, color):
                score += 15 * sign

        for queen in board.pieces(chess.QUEEN, color):
            file = chess.square_file(queen)
            if is_open_file(board, file):
                score += 10 * sign

        # Пешечная структура
        score += evaluate_pawn_structure(board, color) * sign

        # Позиционные фишки
        score += space_advantage(board, color) * sign
        score += piece_connection_bonus(board, color) * sign
        score += piece_mobility(board, color) // 2 * sign

    return score

def move_score(board, move):
    score = 0
    if board.is_capture(move):
        captured_piece = board.piece_at(move.to_square)
        if captured_piece:
            score += 10 * piece_values[captured_piece.piece_type]
    if move.to_square in center_squares:
        score += 20
    piece = board.piece_at(move.from_square)
    if piece and piece.piece_type == chess.PAWN:
        rank = chess.square_rank(move.to_square)
        score += rank * 5 if piece.color == chess.WHITE else (7 - rank) * 5
    return score

def negamax(board, depth, alpha, beta, color):
    if depth == 0 or board.is_game_over():
        return color * evaluate_board(board)

    max_eval = -float('inf')
    legal_moves = sorted(board.legal_moves, key=lambda move: move_score(board, move), reverse=True)

    for move in legal_moves:
        board.push(move)
        eval = -negamax(board, depth - 1, -beta, -alpha, -color)
        board.pop()
        max_eval = max(max_eval, eval)
        alpha = max(alpha, eval)
        if alpha >= beta:
            break
    return max_eval

def choose_move(board, max_time=2.0):
    start = time.time()
    best_move = None
    best_score = -float('inf')
    color = 1 if board.turn == chess.WHITE else -1
    legal_moves = list(board.legal_moves)
    legal_moves.sort(key=lambda move: move_score(board, move), reverse=True)

    depth = 1
    while True:
        current_best = None
        current_best_score = -float('inf')

        for move in legal_moves:
            if time.time() - start > max_time:
                return best_move if best_move else random.choice(legal_moves)

            board.push(move)
            score = -negamax(board, depth - 1, -float('inf'), float('inf'), -color)
            board.pop()

            if score > current_best_score:
                current_best_score = score
                current_best = move

        if time.time() - start > max_time:
            break

        best_move = current_best
        best_score = current_best_score
        depth += 1

    return best_move

def main():
    board = chess.Board()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate 230725dev")
            print("id author Classic")
            print("uciok")
        elif line == "isready":
            print("readyok")
        elif line.startswith("ucinewgame"):
            board.reset()
        elif line.startswith("position"):
            parts = line.split(" ")
            if "startpos" in parts:
                board.reset()
                if "moves" in parts:
                    moves_index = parts.index("moves")
                    moves = parts[moves_index + 1:]
                    for mv in moves:
                        board.push_uci(mv)
            elif "fen" in parts:
                fen_index = parts.index("fen")
                fen_str = " ".join(parts[fen_index + 1:fen_index + 7])
                board.set_fen(fen_str)
                if "moves" in parts:
                    moves_index = parts.index("moves")
                    moves = parts[moves_index + 1:]
                    for mv in moves:
                        board.push_uci(mv)
        elif line.startswith("go"):
            tokens = line.split()
            wtime = btime = None
            if "wtime" in tokens:
                wtime = int(tokens[tokens.index("wtime") + 1]) / 1000.0
            if "btime" in tokens:
                btime = int(tokens[tokens.index("btime") + 1]) / 1000.0

            current_time = wtime if board.turn == chess.WHITE else btime
            if current_time is not None:
                if current_time < 10:
                    think_time = 0.05
                else:
                    think_time = min(3.0, max(0.1, current_time * 0.015))
            else:
                think_time = 2.0

            start_time = time.time()
            move = choose_move(board, think_time)
            elapsed = int((time.time() - start_time) * 1000)

            if move is not None:
                board.push(move)
                eval_score = evaluate_board(board)
                board.pop()
                print(f"info score cp {eval_score} time {elapsed}")
                print("bestmove", move.uci())
            else:
                print("bestmove 0000")
        elif line == "quit":
            break

        sys.stdout.flush()

if __name__ == "__main__":
    main()
