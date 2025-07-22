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
    chess.KING: 0
}

# Piece-Square Tables (PST) для позиционной оценки (белая сторона),
# для черных используется зеркальное отображение
piece_square_tables = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10,-20,-20, 10, 10,  5,
         5, -5,-10,  0,  0,-10, -5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5,  5, 10, 25, 25, 10,  5,  5,
        10, 10, 20, 30, 30, 20, 10, 10,
        50, 50, 50, 50, 50, 50, 50, 50,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -40,-20,  0,  0,  0,  0,-20,-40,
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
         0,  0,  0,  5,  5,  0,  0,  0,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         5, 10, 10, 10, 10, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -10,  5,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ],
    chess.KING: [
        20, 30, 10,  0,  0, 10, 30, 20,
        20, 20,  0,  0,  0,  0, 20, 20,
       -10,-20,-20,-20,-20,-20,-20,-10,
       -20,-30,-30,-40,-40,-30,-30,-20,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30
    ]
}

center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]

def evaluate_board(board, move_history=None):
    # Немедленная проверка на мат/пат
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # Материал и позиционная оценка по PST
    for piece_type in piece_values:
        for square in board.pieces(piece_type, chess.WHITE):
            score += piece_values[piece_type]
            score += piece_square_tables[piece_type][square]
        for square in board.pieces(piece_type, chess.BLACK):
            score -= piece_values[piece_type]
            score -= piece_square_tables[piece_type][chess.square_mirror(square)]

    # Безопасность короля: количество дружественных фигур рядом с королём
    def king_safety(color):
        king_sq = board.king(color)
        if king_sq is None:
            return -9999
        rank = chess.square_rank(king_sq)
        file = chess.square_file(king_sq)
        friendly = 0
        for dr in [-1, 0, 1]:
            for df in [-1, 0, 1]:
                if dr == 0 and df == 0:
                    continue
                r = rank + dr
                f = file + df
                if 0 <= r <= 7 and 0 <= f <= 7:
                    sq = chess.square(f, r)
                    piece = board.piece_at(sq)
                    if piece and piece.color == color:
                        friendly += 1
        return friendly * 10  # вес безопасности короля увеличен

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    # Контроль центра (бонус за занятые центральные поля)
    for sq in center_squares:
        piece = board.piece_at(sq)
        if piece:
            score += 20 if piece.color == chess.WHITE else -20

    # Пешечная структура — штраф за изолированные и удвоенные пешки
    def pawn_structure(color):
        pawns = board.pieces(chess.PAWN, color)
        files = defaultdict(int)
        penalties = 0
        for square in pawns:
            file = chess.square_file(square)
            files[file] += 1
        for f in files:
            if files[f] > 1:
                penalties += 15  # удвоенные пешки — больший штраф
            isolated = all(files.get(adj, 0) == 0 for adj in [f - 1, f + 1])
            if isolated:
                penalties += 20  # изолированные пешки — более серьезный штраф
        return -penalties if color == chess.WHITE else penalties

    score += pawn_structure(chess.WHITE)
    score -= pawn_structure(chess.BLACK)

    # Штраф за повторные ходы одной фигуры в дебюте (темп)
    if move_history:
        moved_pieces = defaultdict(int)
        for move in move_history[-8:]:
            piece = board.piece_at(move.from_square)
            if piece:
                moved_pieces[(piece.piece_type, piece.color, move.from_square)] += 1
        for (ptype, color, _), count in moved_pieces.items():
            if count > 1:
                score += -10 * count if color == chess.WHITE else 10 * count

    return score

def minimax(board, depth, alpha, beta, is_maximizing, move_history=None):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board, move_history), None

    best_move = None
    if is_maximizing:
        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval_score, _ = minimax(board, depth - 1, alpha, beta, False, (move_history or []) + [move])
            board.pop()
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = move
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval_score, _ = minimax(board, depth - 1, alpha, beta, True, (move_history or []) + [move])
            board.pop()
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = move
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move

def main():
    board = chess.Board()
    while not board.is_game_over():
        if board.turn == chess.WHITE:
            # Белые: наш движок
            _, move = minimax(board, 3, -float('inf'), float('inf'), True)
            if move is None:
                break
            board.push(move)
            print(f"White plays: {board.san(move)}")
        else:
            # Черные: случайный ход (можешь заменить на более сильного соперника)
            move = random.choice(list(board.legal_moves))
            board.push(move)
            print(f"Black plays: {board.san(move)}")

        print(board)
        print("-" * 40)

    print("Game over:", board.result())

if __name__ == "__main__":
    main()
