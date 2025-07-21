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
        20, 30, 10, 0, 0, 10, 30, 20,
        20, 20, 0, 0, 0, 0, 20, 20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30
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

    # Material evaluation
    for piece_type in piece_values:
        white_pieces = board.pieces(piece_type, chess.WHITE)
        black_pieces = board.pieces(piece_type, chess.BLACK)
        score += len(white_pieces) * piece_values[piece_type]
        score -= len(black_pieces) * piece_values[piece_type]

    # Piece-square tables
    for piece_type, table in piece_square_tables.items():
        for sq in board.pieces(piece_type, chess.WHITE):
            score += table[sq]
        for sq in board.pieces(piece_type, chess.BLACK):
            score -= table[chess.square_mirror(sq)]

    # King safety using attack units (simple version)
    def king_safety(color):
        king_sq = board.king(color)
        if king_sq is None:
            return -9999
        danger = 0
        attackers = board.attackers(not color, king_sq)
        danger -= len(attackers) * 20
        for sq in square_area(king_sq, 1):
            piece = board.piece_at(sq)
            if piece and piece.color == color:
                danger += 5
        return danger

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    # Activity/mobility: weighted count of legal moves
    mobility_score = 0
    mobility_weights = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0
    }
    for move in board.legal_moves:
        piece = board.piece_at(move.from_square)
        if piece:
            w = mobility_weights[piece.piece_type]
            mobility_score += w if piece.color == chess.WHITE else -w
    score += mobility_score

    # Center control
    center_control = 0
    for sq in center_squares:
        attackers_white = len(board.attackers(chess.WHITE, sq))
        attackers_black = len(board.attackers(chess.BLACK, sq))
        center_control += 10 * (attackers_white - attackers_black)
    score += center_control

    # Pawn structure: doubled, isolated, passed pawns
    def pawn_structure(color):
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]
        file_counts = {f: files.count(f) for f in set(files)}
        score_ps = 0

        # Doubled pawns penalty
        for f, count in file_counts.items():
            if count > 1:
                score_ps -= 25 * (count - 1)

        # Isolated pawns penalty
        for f in set(files):
            if f > 0 and f < 7:
                if f - 1 not in files and f + 1 not in files:
                    score_ps -= 20
            elif f == 0:
                if 1 not in files:
                    score_ps -= 20
            elif f == 7:
                if 6 not in files:
                    score_ps -= 20

        # Passed pawns bonus
        for sq in pawns:
            rank = chess.square_rank(sq)
            file = chess.square_file(sq)
            passed = True
            for opp_sq in board.pieces(chess.PAWN, not color):
                opp_file = chess.square_file(opp_sq)
                opp_rank = chess.square_rank(opp_sq)
                if abs(opp_file - file) <= 1:
                    if (color == chess.WHITE and opp_rank > rank) or (color == chess.BLACK and opp_rank < rank):
                        passed = False
                        break
            if passed:
                score_ps += 30
        return score_ps

    score += pawn_structure(chess.WHITE)
    score -= pawn_structure(chess.BLACK)

    return score

def quiescence(board, alpha, beta, color):
    stand_pat = evaluate_board(board)
    if color:
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
    else:
        if stand_pat <= alpha:
            return alpha
        if beta > stand_pat:
            beta = stand_pat

    for move in board.legal_moves:
        if board.is_capture(move) or board.gives_check(move):
            board.push(move)
            score = -quiescence(board, -beta, -alpha, not color)
            board.pop()

            if color:
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
            else:
                if score <= alpha:
                    return alpha
                if score < beta:
                    beta = score
    return alpha if color else beta

def negamax(board, depth, alpha, beta, color, start_time, time_limit):
    if time.time() - start_time > time_limit:
        raise TimeoutError

    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta, color)

    max_eval = -9999999
    for move in sorted(board.legal_moves, key=lambda m: random.random()):
        board.push(move)
        try:
            eval = -negamax(board, depth - 1, -beta, -alpha, not color, start_time, time_limit)
        except TimeoutError:
            board.pop()
            raise
        board.pop()
        if eval > max_eval:
            max_eval = eval
        if max_eval > alpha:
            alpha = max_eval
        if alpha >= beta:
            break
    return max_eval

def select_move(board, time_left, increment):
    start = time.time()

    # Time control for depth
    if time_left < 3:
        max_depth = 3
        time_limit = 1.5
    elif time_left < 10:
        max_depth = 4
        time_limit = 3
    elif time_left < 60:
        max_depth = 5
        time_limit = 6
    else:
        max_depth = 6
        time_limit = 10

    best_move = None
    best_score = -9999999
    alpha = -10000000
    beta = 10000000

    for depth in range(1, max_depth + 1):
        try:
            for move in board.legal_moves:
                board.push(move)
                score = -negamax(board, depth - 1, -beta, -alpha, not board.turn, start, time_limit)
                board.pop()
                if score > best_score:
                    best_score = score
                    best_move = move
            if time.time() - start > time_limit:
                break
        except TimeoutError:
            break

    if best_move is None:
        return random.choice(list(board.legal_moves))
    return best_move

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline().strip()
        if line == "quit":
            break
        elif line == "uci":
            print("id name SmileyMate")
            print("id author Classic")
            print("uciok")
        elif line == "isready":
            print("readyok")
        elif line.startswith("position startpos moves"):
            moves = line.split()[3:]
            board.reset()
            for move in moves:
                board.push_uci(move)
        elif line.startswith("position fen"):
            fen_parts = line.split(" ", 2)[2].split(" moves ")
            board.set_fen(fen_parts[0])
            if len(fen_parts) > 1:
                for move in fen_parts[1].split():
                    board.push_uci(move)
        elif line.startswith("go"):
            # Parse time control info
            time_left = 60  # default 60 sec
            increment = 0
            for token in line.split():
                if token.startswith("wtime") and board.turn == chess.WHITE:
                    time_left = int(token[5:]) / 1000.0
                if token.startswith("btime") and board.turn == chess.BLACK:
                    time_left = int(token[5:]) / 1000.0
                if token.startswith("winc") and board.turn == chess.WHITE:
                    increment = int(token[4:]) / 1000.0
                if token.startswith("binc") and board.turn == chess.BLACK:
                    increment = int(token[4:]) / 1000.0

            move = select_move(board, time_left, increment)
            print(f"bestmove {move.uci()}")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
