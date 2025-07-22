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

# Полные PST таблицы
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
    return [chess.square(f, r)
            for df in range(-radius, radius + 1)
            for dr in range(-radius, radius + 1)
            if 0 <= (f := file + df) < 8 and 0 <= (r := rank + dr) < 8]

def evaluate_board(board):
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # Material + PST
    for piece_type in piece_values:
        for square in board.pieces(piece_type, chess.WHITE):
            score += piece_values[piece_type]
            score += piece_square_tables[piece_type][square]
        for square in board.pieces(piece_type, chess.BLACK):
            score -= piece_values[piece_type]
            score -= piece_square_tables[piece_type][chess.square_mirror(square)]

    # King safety
    def king_safety(color):
        king_square = board.king(color)
        if king_square is None:
            return -9999
        danger = 0
        attackers = board.attackers(not color, king_square)
        danger -= len(attackers) * 20
        for sq in square_area(king_square, 1):
            piece = board.piece_at(sq)
            if piece and piece.color == color:
                danger += 5
        return danger

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    # Center control
    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

    # Pawn structure: isolated & doubled
    def pawn_structure(color):
        pawns = board.pieces(chess.PAWN, color)
        files = defaultdict(int)
        isolated_penalty = 0
        for square in pawns:
            file = chess.square_file(square)
            files[file] += 1
            # Check isolated
            if not any(board.piece_at(chess.square(f, chess.square_rank(square)))
                       for f in [file - 1, file + 1]
                       if 0 <= f < 8):
                isolated_penalty += 10
        doubled_penalty = sum((count - 1) * 15 for count in files.values() if count > 1)
        return -(isolated_penalty + doubled_penalty)

    score += pawn_structure(chess.WHITE)
    score -= pawn_structure(chess.BLACK)

    # Early queen penalty
    for color in [chess.WHITE, chess.BLACK]:
        queen_square = next(iter(board.pieces(chess.QUEEN, color)), None)
        if queen_square and board.fullmove_number <= 8:
            if chess.square_rank(queen_square) > 1 and chess.square_rank(queen_square) < 6:
                score -= 15 if color == chess.WHITE else -15

    # Repeated piece movement
    if len(board.move_stack) >= 6:
        last_moves = board.move_stack[-6:]
        pieces_moved = [board.piece_at(m.from_square) for m in last_moves]
        if all(p == pieces_moved[0] for p in pieces_moved if p):
            score -= 30 if board.turn == chess.WHITE else -30

    # Development bonus
    def development_bonus(color):
        bonus = 0
        pieces = board.pieces(chess.KNIGHT, color) | board.pieces(chess.BISHOP, color)
        for sq in pieces:
            rank = chess.square_rank(sq)
            if (color == chess.WHITE and rank >= 2) or (color == chess.BLACK and rank <= 5):
                bonus += 10
        return bonus

    score += development_bonus(chess.WHITE)
    score -= development_bonus(chess.BLACK)

    return score

def negamax(board, depth, alpha, beta, color):
    if depth == 0 or board.is_game_over():
        return color * evaluate_board(board)

    max_eval = -float('inf')
    for move in board.legal_moves:
        board.push(move)
        eval = -negamax(board, depth - 1, -beta, -alpha, -color)
        board.pop()
        max_eval = max(max_eval, eval)
        alpha = max(alpha, eval)
        if alpha >= beta:
            break
    return max_eval

def choose_move(board, depth=3):
    best_score = -float('inf')
    best_move = None
    for move in list(board.legal_moves):
        board.push(move)
        score = -negamax(board, depth - 1, -float('inf'), float('inf'), -1)
        board.pop()
        if score > best_score:
            best_score = score
            best_move = move
    return best_move

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if line.startswith("uci"):
            print("id name SmileyMate")
            print("id author OpenAI")
            print("uciok")
        elif line.startswith("isready"):
            print("readyok")
        elif line.startswith("position"):
            parts = line.strip().split()
            if "startpos" in parts:
                board.set_fen(chess.STARTING_FEN)
                moves_index = parts.index("moves") if "moves" in parts else None
                if moves_index:
                    for move_str in parts[moves_index + 1:]:
                        move = chess.Move.from_uci(move_str)
                        board.push(move)
        elif line.startswith("go"):
            move = choose_move(board)
            if move:
                print(f"bestmove {move.uci()}")
            else:
                print("bestmove 0000")
        elif line.startswith("quit"):
            break

if __name__ == "__main__":
    main()
