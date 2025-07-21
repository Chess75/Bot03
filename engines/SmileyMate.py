#!/usr/bin/env python3
import sys
import chess
import random
import time

piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 340,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
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
        -50, -40, -30, -30, -30, -30, -40, -50,
    ],
    chess.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -20, -10, -10, -10, -10, -10, -10, -20,
    ],
    chess.ROOK: [
        0, 0, 0, 5, 5, 0, 0, 0,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        -5, 0, 0, 0, 0, 0, 0, -5,
        5, 10, 10, 10, 10, 10, 10, 5,
        0, 0, 0, 0, 0, 0, 0, 0,
    ],
    chess.QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20,
    ],
    chess.KING: [
        20, 30, 10, 0, 0, 10, 30, 20,
        20, 20, 0, 0, 0, 0, 20, 20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
    ]
}

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
attack_unit = {chess.PAWN: 1, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 5}
transposition_table = {}

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

        table = piece_square_tables.get(piece_type)
        for sq in white:
            if table: score += table[sq]
        for sq in black:
            if table: score -= table[chess.square_mirror(sq)]

    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

    score += mobility_score(board)
    score += pawn_structure(board)
    score += king_safety(board, chess.WHITE)
    score -= king_safety(board, chess.BLACK)

    return score

def mobility_score(board):
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mobility = 0
        for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            for sq in board.pieces(pt, color):
                mobility += len(board.attacks(sq))
        score += mobility * (1 if color == chess.WHITE else -1)
    return score

def pawn_structure(board):
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]
        for sq in pawns:
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)
            if files.count(file) > 1:
                score -= 15 if color == chess.WHITE else -15
            if not any(f in files for f in [file - 1, file + 1]):
                score -= 20 if color == chess.WHITE else -20
            is_passed = True
            for f in [file - 1, file, file + 1]:
                if 0 <= f <= 7:
                    for r in range(rank + 1, 8) if color == chess.WHITE else range(0, rank):
                        sq_check = chess.square(f, r)
                        if board.piece_at(sq_check) == chess.Piece(chess.PAWN, not color):
                            is_passed = False
            if is_passed:
                score += 30 if color == chess.WHITE else -30
    return score

def king_safety(board, color):
    king_sq = board.king(color)
    danger = 0
    for attacker_sq in board.attackers(not color, king_sq):
        piece = board.piece_at(attacker_sq)
        if piece:
            danger += attack_unit.get(piece.piece_type, 0)
    return -danger * 10

def move_score(move, board):
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim and attacker:
            return 10 * piece_values[victim.piece_type] - piece_values[attacker.piece_type]
    if board.gives_check(move):
        return 50
    return 0

def order_moves(board):
    return sorted(board.legal_moves, key=lambda m: move_score(m, board), reverse=True)

def quiescence(board, alpha, beta, color):
    stand_pat = color * evaluate_board(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in board.legal_moves:
        if board.is_capture(move):
            board.push(move)
            score = -quiescence(board, -beta, -alpha, -color)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
    return alpha

def negamax(board, depth, alpha, beta, color):
    key = (board.fen(), depth)
    if key in transposition_table:
        return transposition_table[key]

    if depth == 0:
        return quiescence(board, alpha, beta, color)

    max_eval = -float('inf')
    for move in order_moves(board):
        board.push(move)
        eval = -negamax(board, depth - 1, -beta, -alpha, -color)
        board.pop()
        if eval > max_eval:
            max_eval = eval
        if max_eval > alpha:
            alpha = max_eval
        if alpha >= beta:
            break

    transposition_table[key] = max_eval
    return max_eval

def choose_move(board, time_limit=2.0):
    start_time = time.time()
    color = 1 if board.turn == chess.WHITE else -1

    if time_limit > 20:
        max_depth = 6
    elif time_limit > 15:
        max_depth = 5
    elif time_limit > 10:
        max_depth = 4
    elif time_limit > 5:
        max_depth = 2
    else:
        max_depth = 1

    best_move = None
    best_score = -float('inf')
    depth = 1

    while depth <= max_depth and time.time() - start_time < time_limit:
        current_best = None
        current_best_score = -float('inf')

        for move in order_moves(board):
            board.push(move)
            score = -negamax(board, depth, -float('inf'), float('inf'), -color)
            board.pop()

            if score > current_best_score:
                current_best_score = score
                current_best = move

        if current_best:
            best_score = current_best_score
            best_move = current_best

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
                    moves = parts[parts.index("moves") + 1:]
                    for mv in moves:
                        board.push_uci(mv)
            elif "fen" in parts:
                fen_index = parts.index("fen")
                fen_str = " ".join(parts[fen_index + 1:fen_index + 7])
                board.set_fen(fen_str)
                if "moves" in parts:
                    moves = parts[parts.index("moves") + 1:]
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
            think_time = min(current_time * 0.02, 1.0) if current_time else 1.0

            start_time = time.time()
            move = choose_move(board, current_time or 2.0)
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

