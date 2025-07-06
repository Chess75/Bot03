#!/usr/bin/env python3
import sys
import time
import chess
import random

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3.25,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]

def evaluate_board(board):
    if board.is_checkmate():
        return 10000 if board.turn == chess.BLACK else -10000
    if board.is_stalemate():
        return 0

    score = 0
    for piece_type in piece_values:
        score += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]

    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 0.2 if piece.color == chess.WHITE else -0.2

    for square in chess.SquareSet(chess.BB_BACKRANKS):
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.KING:
            score += 0.5 if piece.color == chess.WHITE else -0.5

    return score

def minimax(board, depth, alpha, beta, start_time, time_limit):
    if depth == 0 or board.is_game_over() or time.time() - start_time > time_limit:
        return evaluate_board(board)

    legal_moves = list(board.legal_moves)
    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, start_time, time_limit)
            board.pop()
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, start_time, time_limit)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def is_blunder(board, move):
    piece = board.piece_at(move.from_square)
    if not piece:
        return False
    board.push(move)
    eval_after = evaluate_board(board)
    board.pop()
    if piece.piece_type == chess.QUEEN and eval_after < -5:
        return True
    return False

def iterative_deepening(board, max_time):
    start_time = time.time()
    best_move = None
    depth = 1
    while True:
        if time.time() - start_time > max_time:
            break
        current_best = None
        best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
        for move in board.legal_moves:
            if is_blunder(board, move):
                continue
            board.push(move)
            score = minimax(board, depth - 1, -float('inf'), float('inf'), start_time, max_time)
            board.pop()

            if board.turn == chess.WHITE:
                if score > best_score:
                    best_score = score
                    current_best = move
            else:
                if score < best_score:
                    best_score = score
                    current_best = move

        if current_best:
            best_move = current_best
        depth += 1
    return best_move

def choose_move(board):
    if board.fullmove_number == 1:
        return iterative_deepening(board, max_time=5.0)

    time_left = 60  # допустим у нас 60 секунд, или можно динамически получать
    if time_left < 10:
        max_time = 0.1
    elif time_left < 30:
        max_time = 0.3
    else:
        max_time = 1.5
    return iterative_deepening(board, max_time=max_time)

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate version 2.0")
            print("id author ClassicGPT")
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
