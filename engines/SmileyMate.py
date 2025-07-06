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
        return -9999 if board.turn else 9999
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

    return score

def quiescence(board, alpha, beta):
    stand_pat = evaluate_board(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in board.legal_moves:
        if board.is_capture(move) or board.gives_check(move):
            board.push(move)
            score = -quiescence(board, -beta, -alpha)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

    return alpha

def alphabeta(board, depth, alpha, beta, start_time, time_limit):
    if time.time() - start_time > time_limit:
        raise TimeoutError()

    if depth == 0:
        return quiescence(board, alpha, beta)

    best_score = -float('inf')
    for move in board.legal_moves:
        board.push(move)
        score = -alphabeta(board, depth - 1, -beta, -alpha, start_time, time_limit)
        board.pop()

        if score >= beta:
            return beta
        if score > best_score:
            best_score = score
        if score > alpha:
            alpha = score

    return best_score

def iterative_deepening(board, max_time):
    start_time = time.time()
    best_move = None
    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    depth = 1

    try:
        while True:
            current_best = None
            for move in board.legal_moves:
                board.push(move)
                score = -alphabeta(board, depth - 1, -float('inf'), float('inf'), start_time, max_time)
                board.pop()

                if board.turn == chess.WHITE and score > best_score:
                    best_score = score
                    current_best = move
                elif board.turn == chess.BLACK and score < best_score:
                    best_score = score
                    current_best = move

            if current_best:
                best_move = current_best
            depth += 1

    except TimeoutError:
        pass

    return best_move

def choose_move(board):
    if board.fullmove_number == 1:
        return iterative_deepening(board, max_time=5.0)

    time_left = 60  # заглушка, можно доработать
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
            print("id name SmileyMate version 2.1")
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
