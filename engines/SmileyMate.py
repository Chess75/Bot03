#!/usr/bin/env python3
import sys
import chess
import random
import time
import re

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
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

def is_passed_pawn(board, square, color):
    file = chess.square_file(square)
    rank = chess.square_rank(square)
    for df in [-1, 0, 1]:
        f = file + df
        if 0 <= f < 8:
            for r in range(rank + 1, 8) if color == chess.WHITE else range(rank - 1, -1, -1):
                sq = chess.square(f, r)
                piece = board.piece_at(sq)
                if piece and piece.piece_type == chess.PAWN and piece.color != color:
                    return False
    return True

def evaluate_board(board):
    if board.is_checkmate():
        return 10000 if board.turn == chess.BLACK else -10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # 1. Материал
    material_score = 0
    for piece_type in piece_values:
        white_count = len(board.pieces(piece_type, chess.WHITE))
        black_count = len(board.pieces(piece_type, chess.BLACK))
        material_score += (white_count - black_count) * piece_values[piece_type]
    score += material_score * 100  # Главный вес

    # 2. Безопасность короля
    def king_safety(color):
        king_square = board.king(color)
        if king_square is None:
            return -9999
        safety = 0
        attackers = board.attackers(not color, king_square)
        safety -= len(attackers) * 50
        for square in square_area(king_square, 1):
            piece = board.piece_at(square)
            if piece and piece.color == color:
                safety += 5
        return safety

    king_safety_score = king_safety(chess.WHITE) - king_safety(chess.BLACK)
    score += king_safety_score * 10

    # 3. Позиционные элементы
    positional_score = 0

    # Piece-square tables (только пешки, пример)
    PST = {
        chess.PAWN: [
            0, 0, 0, 0, 0, 0, 0, 0,
            5, 5, 5, -5, -5, 5, 5, 5,
            1, 1, 2, 3, 3, 2, 1, 1,
            0.5, 0.5, 1, 2.5, 2.5, 1, 0.5, 0.5,
            0, 0, 0, 2, 2, 0, 0, 0,
            0.5, -0.5, -1, 0, 0, -1, -0.5, 0.5,
            0.5, 1, 1, -2, -2, 1, 1, 0.5,
            0, 0, 0, 0, 0, 0, 0, 0
        ],
    }

    for color in [chess.WHITE, chess.BLACK]:
        sign = 1 if color == chess.WHITE else -1
        for piece_type in PST:
            for square in board.pieces(piece_type, color):
                index = square if color == chess.WHITE else chess.square_mirror(square)
                positional_score += sign * PST[piece_type][index]

    # Мобильность
    white_mob = len(list(board.generate_legal_moves(chess.WHITE)))
    black_mob = len(list(board.generate_legal_moves(chess.BLACK)))
    positional_score += (white_mob - black_mob) * 0.1

    # Контроль центра
    for square in center_squares:
        attackers_white = board.attackers(chess.WHITE, square)
        attackers_black = board.attackers(chess.BLACK, square)
        positional_score += (len(attackers_white) - len(attackers_black)) * 0.2

    # Пешечная структура
    def pawn_structure(color):
        score = 0
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(p) for p in pawns]
        file_counts = {f: files.count(f) for f in set(files)}

        for f, count in file_counts.items():
            if count > 1:
                score -= 0.5 * (count - 1)

        for p in pawns:
            file = chess.square_file(p)
            isolated = True
            for df in [-1, 1]:
                f2 = file + df
                if 0 <= f2 < 8:
                    if any(chess.square_file(other) == f2 for other in pawns):
                        isolated = False
                        break
            if isolated:
                score -= 0.5

            if is_passed_pawn(board, p, color):
                score += 1.0
        return score

    positional_score += pawn_structure(chess.WHITE)
    positional_score -= pawn_structure(chess.BLACK)

    score += positional_score  # Меньший вес
    return score

def minimax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta)
            board.pop()
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def choose_move(board, time_limit=1.0):
    best_move = None
    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    start_time = time.time()
    depth = 1

    while True:
        if time.time() - start_time > time_limit:
            break

        current_best = None
        current_best_score = -float('inf') if board.turn == chess.WHITE else float('inf')

        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, depth, -float('inf'), float('inf'))
            board.pop()

            if board.turn == chess.WHITE:
                if score > current_best_score:
                    current_best_score = score
                    current_best = move
            else:
                if score < current_best_score:
                    current_best_score = score
                    current_best = move

        if current_best is not None:
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
            print("id name SmileyMate version 2.0")
            print("id author Classic+GPT")
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
            time_limit = 1.0  # default
            wtime = btime = 0

            match = re.search(r"wtime (\d+)", line)
            if match:
                wtime = int(match.group(1)) / 1000
            match = re.search(r"btime (\d+)", line)
            if match:
                btime = int(match.group(1)) / 1000

            if board.turn == chess.WHITE and wtime:
                time_limit = max(0.05, wtime / 40)
            elif board.turn == chess.BLACK and btime:
                time_limit = max(0.05, btime / 40)

            move = choose_move(board, time_limit)
            if move is not None:
                print("bestmove", move.uci())
            else:
                print("bestmove 0000")
        elif line == "quit":
            break

        sys.stdout.flush()

if __name__ == "__main__":
    main()
