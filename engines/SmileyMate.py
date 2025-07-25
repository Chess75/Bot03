#!/usr/bin/env python3
import sys
import chess
import random
import time
import hashlib

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
transposition_table = {}

def zobrist_hash(board):
    return hashlib.md5(board.board_fen().encode()).hexdigest()

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

def penalize_undefended_pieces(board):
    penalty = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.color == board.turn:
            attackers = board.attackers(not board.turn, square)
            defenders = board.attackers(board.turn, square)
            if attackers and not defenders:
                penalty -= piece_values[piece.piece_type] // 3
    return penalty

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

    score += penalize_undefended_pieces(board)
    score += len(list(board.legal_moves)) * (1 if board.turn == chess.WHITE else -1)

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
    if piece:
        if piece.piece_type == chess.PAWN:
            rank = chess.square_rank(move.to_square)
            score += rank * 5 if piece.color == chess.WHITE else (7 - rank) * 5
        if piece.piece_type == chess.KNIGHT:
            if chess.square_file(move.to_square) in [0, 7] or chess.square_rank(move.to_square) in [0, 7]:
                score -= 15
    if board.gives_check(move):
        score += 30
    return score

def negamax(board, depth, alpha, beta, color):
    h = zobrist_hash(board)
    if h in transposition_table and transposition_table[h]['depth'] >= depth:
        return transposition_table[h]['value']

    if depth == 0 or board.is_game_over():
        eval = color * evaluate_board(board)
        transposition_table[h] = {'depth': depth, 'value': eval}
        return eval

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

    transposition_table[h] = {'depth': depth, 'value': max_eval}
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
                return current_best if current_best else random.choice(legal_moves)

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

    return best_move if best_move else random.choice(legal_moves)

def main():
    board = chess.Board()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate")
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
            think_time = max(0.1, min(current_time * 0.015, 3.0)) if current_time else 2.0

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
