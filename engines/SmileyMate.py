#!/usr/bin/env python3
import sys
import chess
import random
import time

piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Piece-square tables
piece_square_tables = {
    chess.PAWN: [
          0,  0,  0,  0,  0,  0,  0,  0,
         50, 50, 50, 50, 50, 50, 50, 50,
         10, 10, 20, 30, 30, 20, 10, 10,
          5,  5, 10, 25, 25, 10,  5,  5,
          0,  0,  0, 20, 20,  0,  0,  0,
          5, -5,-10,  0,  0,-10, -5,  5,
          5, 10, 10,-20,-20, 10, 10,  5,
          0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ],
    chess.ROOK: [
          0,  0,  0,  0,  0,  0,  0,  0,
          5, 10, 10, 10, 10, 10, 10,  5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
         -5,  0,  0,  0,  0,  0,  0, -5,
          0,  0,  0,  5,  5,  0,  0,  0
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ],
    chess.KING: [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20
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

def evaluate_board(board):
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    white_material = 0
    black_material = 0

    for piece_type in piece_values:
        white_pieces = board.pieces(piece_type, chess.WHITE)
        black_pieces = board.pieces(piece_type, chess.BLACK)
        white_material += len(white_pieces) * piece_values[piece_type]
        black_material += len(black_pieces) * piece_values[piece_type]
        score += len(white_pieces) * piece_values[piece_type]
        score -= len(black_pieces) * piece_values[piece_type]

        for square in white_pieces:
            score += piece_square_tables[piece_type][square]
        for square in black_pieces:
            score -= piece_square_tables[piece_type][chess.square_mirror(square)]

    for square in board.pieces(chess.PAWN, chess.WHITE):
        if chess.square_rank(square) == 6:
            score += 25
    for square in board.pieces(chess.PAWN, chess.BLACK):
        if chess.square_rank(square) == 1:
            score -= 25

    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += 40
    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        score -= 40

    def count_islands(color):
        files_with_pawns = set(chess.square_file(sq) for sq in board.pieces(chess.PAWN, color))
        islands = 0
        for f in range(8):
            if f in files_with_pawns and (f - 1 not in files_with_pawns):
                islands += 1
        return islands

    score -= 10 * count_islands(chess.WHITE)
    score += 10 * count_islands(chess.BLACK)

    for square in board.pieces(chess.ROOK, chess.WHITE):
        file = chess.square_file(square)
        has_white_pawn = any(chess.square_file(p) == file for p in board.pieces(chess.PAWN, chess.WHITE))
        has_black_pawn = any(chess.square_file(p) == file for p in board.pieces(chess.PAWN, chess.BLACK))
        if not has_white_pawn and not has_black_pawn:
            score += 30
        elif not has_white_pawn:
            score += 15

    for square in board.pieces(chess.ROOK, chess.BLACK):
        file = chess.square_file(square)
        has_black_pawn = any(chess.square_file(p) == file for p in board.pieces(chess.PAWN, chess.BLACK))
        has_white_pawn = any(chess.square_file(p) == file for p in board.pieces(chess.PAWN, chess.WHITE))
        if not has_black_pawn and not has_white_pawn:
            score -= 30
        elif not has_black_pawn:
            score -= 15

    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

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
        if (color == chess.WHITE and white_material < 1400) or (color == chess.BLACK and black_material < 1400):
            if chess.square_file(king_square) in [3,4] and chess.square_rank(king_square) in [3,4]:
                danger -= 30
        return danger

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    score += len(list(board.legal_moves)) * (1 if board.turn == chess.WHITE else -1)
    return score


def negamax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)
    max_eval = -float('inf')
    for move in board.legal_moves:
        board.push(move)
        eval = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()
        max_eval = max(max_eval, eval)
        alpha = max(alpha, eval)
        if alpha >= beta:
            break
    return max_eval

def choose_move(board, depth):
    best_score = -float('inf')
    best_move = None
    for move in board.legal_moves:
        board.push(move)
        score = -negamax(board, depth - 1, -float('inf'), float('inf'))
        board.pop()
        if score > best_score:
            best_score = score
            best_move = move
    return best_move

def main():
    board = chess.Board()
    while not board.is_game_over():
        print(board)
        if board.turn:
            move = choose_move(board, 2)
        else:
            move = random.choice(list(board.legal_moves))
        board.push(move)
        time.sleep(0.5)

    print(board)
    print("Game over")

if __name__ == "__main__":
    main()
