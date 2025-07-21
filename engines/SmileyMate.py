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

piece_square_tables = {
    chess.PAWN: [
        0, 0, 0, 0, 0, 0, 0, 0,
        5, 5, 5, -5, -5, 5, 5, 5,
        1, 1, 2, 3, 3, 2, 1, 1,
        0.5, 0.5, 1, 2.5, 2.5, 1, 0.5, 0.5,
        0, 0, 0, 2, 2, 0, 0, 0,
        0.5, -0.5, -1, 0, 0, -1, -0.5, 0.5,
        0.5, 1, 1, -2, -2, 1, 1, 0.5,
        0, 0, 0, 0, 0, 0, 0, 0
    ],
    chess.KNIGHT: [
        -5, -4, -3, -3, -3, -3, -4, -5,
        -4, -2, 0, 0.5, 0.5, 0, -2, -4,
        -3, 0.5, 1, 1.5, 1.5, 1, 0.5, -3,
        -3, 0, 1.5, 2, 2, 1.5, 0, -3,
        -3, 0.5, 1.5, 2, 2, 1.5, 0.5, -3,
        -3, 0, 1, 1.5, 1.5, 1, 0, -3,
        -4, -2, 0, 0, 0, 0, -2, -4,
        -5, -4, -3, -3, -3, -3, -4, -5
    ],
    chess.BISHOP: [0] * 64,
    chess.ROOK: [0] * 64,
    chess.QUEEN: [0] * 64,
    chess.KING: [0] * 64,
}

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
        return -10000 if board.turn else 10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # 1. Material
    for piece_type in piece_values:
        white = board.pieces(piece_type, chess.WHITE)
        black = board.pieces(piece_type, chess.BLACK)
        score += len(white) * piece_values[piece_type]
        score -= len(black) * piece_values[piece_type]

    # 2. King Safety
    def king_safety(color):
        ksq = board.king(color)
        if ksq is None:
            return -999
        attackers = board.attackers(not color, ksq)
        safety = -len(attackers) * 0.5
        for sq in square_area(ksq, 1):
            piece = board.piece_at(sq)
            if piece and piece.color == color:
                safety += 0.1
        return safety

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    # 3. Piece-square tables
    for piece_type in piece_square_tables:
        table = piece_square_tables[piece_type]
        for sq in board.pieces(piece_type, chess.WHITE):
            score += table[sq]
        for sq in board.pieces(piece_type, chess.BLACK):
            score -= table[chess.square_mirror(sq)]

    # 4. Mobility
    score += 0.1 * len(list(board.legal_moves)) * (1 if board.turn == chess.WHITE else -1)

    # 5. Center control
    for sq in center_squares:
        attackers_white = board.attackers(chess.WHITE, sq)
        attackers_black = board.attackers(chess.BLACK, sq)
        score += 0.1 * len(attackers_white)
        score -= 0.1 * len(attackers_black)

    return score

def minimax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta)
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
            eval = minimax(board, depth - 1, alpha, beta)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def choose_at_depth(board, depth):
    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    best_move = None

    for move in board.legal_moves:
        board.push(move)
        score = minimax(board, depth - 1, -float('inf'), float('inf'))
        board.pop()
        if board.turn == chess.WHITE and score > best_score:
            best_score = score
            best_move = move
        elif board.turn == chess.BLACK and score < best_score:
            best_score = score
            best_move = move

    return best_move, best_score

def choose_move(board, time_left):
    if time_left < 6.0:
        return random.choice(list(board.legal_moves))

    start = time.time()
    best_move = None

    for depth in range(1, 10):
        if time.time() - start > time_left * 0.9:
            break
        move, score = choose_at_depth(board, depth)
        if move:
            best_move = move

    return best_move if best_move else random.choice(list(board.legal_moves))

def main():
    board = chess.Board()
    wtime = btime = winc = binc = 0

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate version 2.0")
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
                    for mv in parts[moves_index + 1:]:
                        board.push_uci(mv)
            elif "fen" in parts:
                fen_index = parts.index("fen")
                fen = " ".join(parts[fen_index + 1:fen_index + 7])
                board.set_fen(fen)
                if "moves" in parts:
                    moves_index = parts.index("moves")
                    for mv in parts[moves_index + 1:]:
                        board.push_uci(mv)
        elif line.startswith("go"):
            tokens = line.split()
            wtime = btime = winc = binc = 0
            if "wtime" in tokens:
                wtime = int(tokens[tokens.index("wtime") + 1]) / 1000
            if "btime" in tokens:
                btime = int(tokens[tokens.index("btime") + 1]) / 1000
            if "winc" in tokens:
                winc = int(tokens[tokens.index("winc") + 1]) / 1000
            if "binc" in tokens:
                binc = int(tokens[tokens.index("binc") + 1]) / 1000

            time_left = wtime if board.turn == chess.WHITE else btime
            move = choose_move(board, time_left)
            print("bestmove", move.uci())
        elif line == "quit":
            break

        sys.stdout.flush()

if __name__ == "__main__":
    main()
