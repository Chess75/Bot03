#!/usr/bin/env python3
import sys
import chess
import random
import time
import concurrent.futures
import threading

lock = threading.Lock()
transposition_table = {}

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

# --- Пешечная структура ---
def evaluate_pawn_structure(board, color):
    score = 0
    pawns = board.pieces(chess.PAWN, color)
    files = [0] * 8

    for square in pawns:
        file = chess.square_file(square)
        files[file] += 1

    for i in range(8):
        if files[i] > 1:
            score -= 10 * (files[i] - 1)
        if files[i] > 0:
            isolated = True
            if i > 0 and files[i - 1] > 0:
                isolated = False
            if i < 7 and files[i + 1] > 0:
                isolated = False
            if isolated:
                score -= 15
    return score

def square_area(square, radius):
    file = chess.square_file(square)
    rank = chess.square_rank(square)
    return [
        chess.square(f, r)
        for df in range(-radius, radius + 1)
        for dr in range(-radius, radius + 1)
        if 0 <= (f := file + df) < 8 and 0 <= (r := rank + dr) < 8
    ]

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]

def evaluate_board(board):
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for piece_type in piece_values:
        white = board.pieces(piece_type, chess.WHITE)
        black = board.pieces(piece_type, chess.BLACK)
        score += len(white) * piece_values[piece_type]
        score -= len(black) * piece_values[piece_type]

    for piece_type, table in piece_square_tables.items():
        for sq in board.pieces(piece_type, chess.WHITE):
            score += table[sq]
        for sq in board.pieces(piece_type, chess.BLACK):
            score -= table[chess.square_mirror(sq)]

    def king_safety(color):
        king_sq = board.king(color)
        if king_sq is None:
            return -9999
        danger = -len(board.attackers(not color, king_sq)) * 20
        for sq in square_area(king_sq, 1):
            piece = board.piece_at(sq)
            if piece and piece.color == color:
                danger += 5
        return danger

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    score += evaluate_pawn_structure(board, chess.WHITE)
    score -= evaluate_pawn_structure(board, chess.BLACK)

    for sq in center_squares:
        piece = board.piece_at(sq)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

    return score

# --- Quiescence Search ---
def quiescence(board, alpha, beta, color):
    stand_pat = color * evaluate_board(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in board.legal_moves:
        if not board.is_capture(move):
            continue
        board.push(move)
        score = -quiescence(board, -beta, -alpha, -color)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

# --- Negamax with TT and quiescence ---
def negamax(board, depth, alpha, beta, color):
    key = (board.board_fen(), board.turn, depth)
    with lock:
        if key in transposition_table:
            return transposition_table[key]

    if depth == 0:
        return quiescence(board, alpha, beta, color)

    max_eval = -float('inf')
    legal_moves = sorted(board.legal_moves, key=lambda m: move_score(board, m), reverse=True)

    for move in legal_moves:
        board.push(move)
        eval = -negamax(board, depth - 1, -beta, -alpha, -color)
        board.pop()
        max_eval = max(max_eval, eval)
        alpha = max(alpha, eval)
        if alpha >= beta:
            break

    with lock:
        transposition_table[key] = max_eval
    return max_eval

def move_score(board, move):
    score = 0
    if board.is_capture(move):
        cap = board.piece_at(move.to_square)
        atk = board.piece_at(move.from_square)
        if cap and atk:
            score += 10 * piece_values[cap.piece_type] - piece_values[atk.piece_type]
    if move.to_square in center_squares:
        score += 20
    if board.gives_check(move):
        score += 30
    piece = board.piece_at(move.from_square)
    if piece and piece.piece_type == chess.PAWN:
        rank = chess.square_rank(move.to_square)
        score += rank * 5 if piece.color == chess.WHITE else (7 - rank) * 5
    return score

# --- Параллельный выбор лучшего хода ---
def choose_move(board, max_time=2.0):
    start = time.time()
    best_move = None
    best_score = -float('inf')
    color = 1 if board.turn == chess.WHITE else -1
    legal_moves = list(board.legal_moves)
    legal_moves.sort(key=lambda m: move_score(board, m), reverse=True)

    depth = 1
    while True:
        time_left = max_time - (time.time() - start)
        if time_left <= 0:
            break

        def evaluate(move):
            b = board.copy()
            b.push(move)
            return move, -negamax(b, depth - 1, -float('inf'), float('inf'), -color)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_scores = list(executor.map(evaluate, legal_moves))

        current_best = max(future_scores, key=lambda x: x[1], default=(None, -float('inf')))
        if time.time() - start > max_time:
            break

        best_move, best_score = current_best
        depth += 1

    return best_move if best_move else random.choice(legal_moves)

# --- UCI интерфейс ---
def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate")
            print("id author Improved")
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
                    for mv in parts[parts.index("moves") + 1:]:
                        board.push_uci(mv)
            elif "fen" in parts:
                idx = parts.index("fen")
                board.set_fen(" ".join(parts[idx + 1:idx + 7]))
                if "moves" in parts:
                    for mv in parts[parts.index("moves") + 1:]:
                        board.push_uci(mv)
        elif line.startswith("go"):
            tokens = line.split()
            wtime = btime = None
            if "wtime" in tokens:
                wtime = int(tokens[tokens.index("wtime") + 1]) / 1000
            if "btime" in tokens:
                btime = int(tokens[tokens.index("btime") + 1]) / 1000

            current_time = wtime if board.turn == chess.WHITE else btime
            think_time = max(0.1, min(current_time * 0.015, 3.0)) if current_time else 2.0

            start_time = time.time()
            move = choose_move(board, think_time)
            elapsed = int((time.time() - start_time) * 1000)

            if move:
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
