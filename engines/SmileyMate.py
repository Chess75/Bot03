#!/usr/bin/env python3
import sys
import chess
import random

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]

# Таблицы ценности для фигур по квадратам (piece-square tables)
piece_square_tables = {
    chess.PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 5, 5,-10,-10, 5, 5, 5,
        1, 1, 2, 3, 3, 2, 1, 1,
        0.5,0.5,1,2.5,2.5,1,0.5,0.5,
        0, 0, 0, 2, 2, 0, 0, 0,
        0.5,-0.5,-1, 0, 0,-1,-0.5,0.5,
        0.5,1,1,-2,-2,1,1,0.5,
        0, 0, 0, 0, 0, 0, 0, 0
    ],
    chess.KNIGHT: [
        -5,-4,-3,-3,-3,-3,-4,-5,
        -4,-2, 0, 0, 0, 0,-2,-4,
        -3, 0, 1.5, 2, 2, 1.5, 0,-3,
        -3, 0.5, 2, 3, 3, 2, 0.5,-3,
        -3, 0, 2, 3, 3, 2, 0,-3,
        -3, 0.5, 1.5, 2, 2, 1.5, 0.5,-3,
        -4,-2, 0, 0.5, 0.5, 0,-2,-4,
        -5,-4,-3,-3,-3,-3,-4,-5
    ],
    # Для упрощения другие фигуры без таблиц (можно добавить позже)
}

def get_piece_square_value(piece_type, color, square):
    table = piece_square_tables.get(piece_type)
    if not table:
        return 0
    # для черных доска зеркальна (переворачиваем индекс)
    return table[square if color == chess.WHITE else chess.square_mirror(square)]

def king_safety(board, color):
    # Простой штраф, если король "открыт"
    king_square = board.king(color)
    if king_square is None:
        return 0
    # Проверяем пешки рядом с королём (перед ним и сбоку)
    rank = chess.square_rank(king_square)
    file = chess.square_file(king_square)
    penalty = 0
    for df in [-1, 0, 1]:
        f = file + df
        if 0 <= f <= 7:
            for dr in [1, 0]:
                r = rank + (dr if color == chess.WHITE else -dr)
                if 0 <= r <= 7:
                    sq = chess.square(f, r)
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.PAWN and piece.color == color:
                        penalty -= 0.2  # бонус, если есть пешка рядом
    return penalty

def evaluate_board(board):
    if board.is_checkmate():
        # Если ход черных и мат — значит белые выиграли и наоборот
        return 10000 if board.turn == chess.BLACK else -10000
    if board.is_stalemate():
        return 0

    score = 0
    for piece_type in piece_values:
        for square in board.pieces(piece_type, chess.WHITE):
            score += piece_values[piece_type] + get_piece_square_value(piece_type, chess.WHITE, square)
        for square in board.pieces(piece_type, chess.BLACK):
            score -= piece_values[piece_type] + get_piece_square_value(piece_type, chess.BLACK, square)

    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 0.2 if piece.color == chess.WHITE else -0.2

    score += king_safety(board, chess.WHITE)
    score -= king_safety(board, chess.BLACK)

    return score

def move_ordering(board, moves):
    # Ходы с захватами или шахом считаются приоритетными
    def move_value(move):
        value = 0
        if board.is_capture(move):
            captured = board.piece_at(move.to_square)
            if captured:
                value += piece_values.get(captured.piece_type, 0) * 10  # множитель для приоритета
        board.push(move)
        if board.is_check():
            value += 5
        board.pop()
        return value
    return sorted(moves, key=move_value, reverse=True)

def minimax(board, depth, alpha=-float('inf'), beta=float('inf')):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    legal_moves = move_ordering(board, list(board.legal_moves))

    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta)
            board.pop()
            if eval > max_eval:
                max_eval = eval
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta)
            board.pop()
            if eval < min_eval:
                min_eval = eval
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def choose_move(board):
    if board.fullmove_number == 1:
        return random.choice(list(board.legal_moves))

    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    best_moves = []

    for move in move_ordering(board, list(board.legal_moves)):
        board.push(move)
        score = minimax(board, 3)  # глубина 3 — чуть глубже
        board.pop()

        if board.turn == chess.WHITE:
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)
        else:
            if score < best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

    return random.choice(best_moves) if best_moves else None

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate version 1.0.4")
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
            move = choose_move(board)
            if move is not None:
                print("bestmove", move.uci())
            else:
                print("bestmove 0000")
        elif line == "quit":
            break

        sys.stdout.flush()

if __name__ == "__main__":
    main()

