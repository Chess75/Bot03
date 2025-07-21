#!/usr/bin/env python3
import sys
import chess
import time
import random

piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}

pst_mg = {
    chess.PAWN: [...],  # Вставим таблицы из предыдущего ответа
    chess.KNIGHT: [...],
    chess.BISHOP: [...],
    chess.ROOK: [...],
    chess.QUEEN: [...],
    chess.KING: [...]
}

pst_eg_king = [...]  # Таблица эндшпиля для короля

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
transposition_table = {}
pv_table = {}

def is_endgame(board):
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    minors_majors = sum(len(board.pieces(pt, True)) + len(board.pieces(pt, False))
                        for pt in [chess.ROOK, chess.BISHOP, chess.KNIGHT])
    return queens == 0 or minors_majors <= 6

def square_area(square, radius):
    file = chess.square_file(square)
    rank = chess.square_rank(square)
    return [chess.square(f, r) for df in range(-radius, radius + 1)
            for dr in range(-radius, radius + 1)
            if 0 <= (f := file + df) < 8 and 0 <= (r := rank + dr) < 8]

def evaluate_board(board):
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    endgame = is_endgame(board)

    for piece_type in piece_values:
        for square in board.pieces(piece_type, chess.WHITE):
            score += piece_values[piece_type]
            if piece_type in pst_mg:
                table = pst_eg_king if piece_type == chess.KING and endgame else pst_mg[piece_type]
                score += table[square]
        for square in board.pieces(piece_type, chess.BLACK):
            score -= piece_values[piece_type]
            if piece_type in pst_mg:
                table = pst_eg_king if piece_type == chess.KING and endgame else pst_mg[piece_type]
                score -= table[chess.square_mirror(square)]

    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

    def king_safety(color):
        king_square = board.king(color)
        if king_square is None:
            return -9999
        attackers = board.attackers(not color, king_square)
        safe_bonus = sum(5 for sq in square_area(king_square, 1)
                         if (p := board.piece_at(sq)) and p.color == color)
        return -20 * len(attackers) + safe_bonus

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    return score if board.turn == chess.WHITE else -score

def order_moves(board):
    moves = list(board.legal_moves)
    def move_score(move):
        score = 0
        if board.is_capture(move):
            score += 10_000
        if board.gives_check(move):
            score += 5_000
        return score
    return sorted(moves, key=move_score, reverse=True)

def minimax(board, depth, alpha, beta, pv=[]):
    key = board.board_fen() + str(depth) + str(board.turn)
    if key in transposition_table:
        return transposition_table[key]

    if depth == 0 or board.is_game_over():
        eval = evaluate_board(board)
        transposition_table[key] = eval
        return eval

    best_score = -float('inf')
    best_line = []

    for move in order_moves(board):
        board.push(move)
        line = []
        score = -minimax(board, depth - 1, -beta, -alpha, line)
        board.pop()

        if score > best_score:
            best_score = score
            best_line = [move] + line
        alpha = max(alpha, score)
        if alpha >= beta:
            break

    if pv is not None:
        pv.clear()
        pv.extend(best_line)
    transposition_table[key] = best_score
    return best_score

def choose_move(board, time_limit=2.0):
    start_time = time.time()
    depth = 1
    best_move = None
    pv = []

    while time.time() - start_time < time_limit:
        current_pv = []
        score = minimax(board, depth, -float('inf'), float('inf'), current_pv)
        if current_pv:
            best_move = current_pv[0]
            pv_table[depth] = (score, list(current_pv))
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
            print("id name SmileyMate++")
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
                fen = " ".join(parts[parts.index("fen") + 1:parts.index("moves")] if "moves" in parts else parts[parts.index("fen") + 1:])
                board.set_fen(fen)
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
            think_time = min(current_time * 0.02, 2.0) if current_time else 2.0

            move = choose_move(board, think_time)
            if move:
                board.push(move)
                score = evaluate_board(board)
                board.pop()
                print(f"info score cp {score} pv {' '.join(m.uci() for m in pv_table.get(max(pv_table, default=0), (0, []))[1])}")
                print("bestmove", move.uci())
            else:
                print("bestmove 0000")
        elif line == "quit":
            break
        sys.stdout.flush()

if __name__ == "__main__":
    main()
