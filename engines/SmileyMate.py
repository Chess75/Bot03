#!/usr/bin/env python3
import sys
import chess
import random
import time

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

def evaluate_board(board):
    if board.is_checkmate():
        return 10000 if board.turn == chess.BLACK else -10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # 1. Материал
    for piece_type in piece_values:
        white_pieces = board.pieces(piece_type, chess.WHITE)
        black_pieces = board.pieces(piece_type, chess.BLACK)
        score += len(white_pieces) * piece_values[piece_type]
        score -= len(black_pieces) * piece_values[piece_type]

    # 2. Безопасность короля
    def king_safety(color):
        king_square = board.king(color)
        if king_square is None:
            return -9999
        danger = 0
        attackers = board.attackers(not color, king_square)
        danger -= len(attackers) * 0.5
        for square in square_area(king_square, 1):
            piece = board.piece_at(square)
            if piece and piece.color == color:
                danger += 0.1
        return danger

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    # 3. Центр
    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 0.2 if piece.color == chess.WHITE else -0.2

    # 4. Развитие
    for piece_type in [chess.KNIGHT, chess.BISHOP]:
        for sq in board.pieces(piece_type, chess.WHITE):
            if chess.square_rank(sq) > 1:
                score += 0.1
        for sq in board.pieces(piece_type, chess.BLACK):
            if chess.square_rank(sq) < 6:
                score -= 0.1

    return score

def minimax(board, depth, alpha, beta, start_time, max_time):
    if time.time() - start_time >= max_time:
        raise TimeoutError()

    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, start_time, max_time)
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
            eval = minimax(board, depth - 1, alpha, beta, start_time, max_time)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def choose_move(board, max_time=1.0):
    start_time = time.time()
    best_move = None
    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')

    depth = 1
    while True:
        if time.time() - start_time >= max_time:
            break

        current_best = None
        current_best_score = -float('inf') if board.turn == chess.WHITE else float('inf')

        for move in list(board.legal_moves):
            board.push(move)
            try:
                score = minimax(board, depth - 1, -float('inf'), float('inf'), start_time, max_time)
            except TimeoutError:
                board.pop()
                break
            board.pop()

            if board.turn == chess.WHITE:
                if score > current_best_score:
                    current_best_score = score
                    current_best = move
            else:
                if score < current_best_score:
                    current_best_score = score
                    current_best = move

        if current_best:
            best_move = current_best
            best_score = current_best_score

        depth += 1

    return best_move if best_move else random.choice(list(board.legal_moves))

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate version 1.2")
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
            move = choose_move(board, max_time=1.0)  # можно настраивать время
            if move is not None:
                print("bestmove", move.uci())
            else:
                print("bestmove 0000")
        elif line == "quit":
            break

        sys.stdout.flush()

if __name__ == "__main__":
    main()

