#!/usr/bin/env python3
import sys
import chess
import random
import time
from collections import defaultdict

piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}

# Full PST for all pieces (WHITE perspective)
# Black uses mirror
piece_square_tables = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10,-20,-20, 10, 10,  5,
         5, -5,-10,  0,  0,-10, -5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5,  5, 10, 25, 25, 10,  5,  5,
        10, 10, 20, 30, 30, 20, 10, 10,
        50, 50, 50, 50, 50, 50, 50, 50,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ],
    chess.ROOK: [
         0,  0,  0,  5,  5,  0,  0,  0,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         5, 10, 10, 10, 10, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -10,  5,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ],
    chess.KING: [
        20, 30, 10,  0,  0, 10, 30, 20,
        20, 20,  0,  0,  0,  0, 20, 20,
       -10,-20,-20,-20,-20,-20,-20,-10,
       -20,-30,-30,-40,-40,-30,-30,-20,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30
    ]
}

center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]

def evaluate_board(board, move_history=None):
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    for piece_type in piece_values:
        for square in board.pieces(piece_type, chess.WHITE):
            score += piece_values[piece_type]
            score += piece_square_tables[piece_type][square]
        for square in board.pieces(piece_type, chess.BLACK):
            score -= piece_values[piece_type]
            score -= piece_square_tables[piece_type][chess.square_mirror(square)]

    # King safety (nearby friendly pieces)
    def king_safety(color):
        king_sq = board.king(color)
        if king_sq is None:
            return -9999
        nearby = chess.SquareSet(chess.square_ring(king_sq))
        friendly = sum(1 for sq in nearby if board.piece_at(sq) and board.color_at(sq) == color)
        return friendly * 5

    score += king_safety(chess.WHITE)
    score -= king_safety(chess.BLACK)

    # Center control
    for sq in center_squares:
        piece = board.piece_at(sq)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

    # Pawn structure
    def pawn_structure(color):
        pawns = board.pieces(chess.PAWN, color)
        files = defaultdict(int)
        penalties = 0
        for square in pawns:
            file = chess.square_file(square)
            files[file] += 1
        for f in files:
            if files[f] > 1:
                penalties += 10  # doubled
            isolated = all(files.get(adj, 0) == 0 for adj in [f - 1, f + 1])
            if isolated:
                penalties += 10
        return -penalties if color == chess.WHITE else penalties

    score += pawn_structure(chess.WHITE)
    score -= pawn_structure(chess.BLACK)

    # Tempo penalty: moving same piece too often in opening
    if move_history:
        moved_pieces = defaultdict(int)
        for move in move_history[-8:]:
            piece = board.piece_at(move.from_square)
            if piece:
                moved_pieces[(piece.piece_type, piece.color, move.from_square)] += 1
        for (ptype, color, _), count in moved_pieces.items():
            if count > 1:
                penalty = (count - 1) * 5
                score -= penalty if color == chess.WHITE else -penalty

    # Early queen development
    for color in [chess.WHITE, chess.BLACK]:
        queen_sq = next(iter(board.pieces(chess.QUEEN, color)), None)
        if queen_sq is not None and (queen_sq not in [chess.D1, chess.D8]):
            if board.fullmove_number < 10:
                score -= 15 if color == chess.WHITE else -15

    return score

def order_moves(board):
    captures = []
    quiets = []
    for move in board.legal_moves:
        if board.is_capture(move):
            captures.append(move)
        else:
            quiets.append(move)
    return captures + quiets

def negamax(board, depth, alpha, beta, color, move_history):
    if depth == 0 or board.is_game_over():
        return color * evaluate_board(board, move_history)

    max_eval = -float('inf')
    for move in order_moves(board):
        board.push(move)
        move_history.append(move)
        eval = -negamax(board, depth - 1, -beta, -alpha, -color, move_history)
        move_history.pop()
        board.pop()
        max_eval = max(max_eval, eval)
        alpha = max(alpha, eval)
        if alpha >= beta:
            break
    return max_eval

def choose_move(board, time_limit=2.0):
    start_time = time.time()
    best_score = -float('inf')
    best_moves = []
    move_history = []

    for move in order_moves(board):
        if time.time() - start_time > time_limit:
            break
        board.push(move)
        move_history.append(move)
        score = -negamax(board, 2, -float('inf'), float('inf'), -1 if board.turn else 1, move_history)
        move_history.pop()
        board.pop()

        if score > best_score:
            best_score = score
            best_moves = [move]
        elif score == best_score:
            best_moves.append(move)

    if not best_moves:
        return random.choice(list(board.legal_moves))
    return random.choice(best_moves)

def main():
    board = chess.Board()
    move_history = []

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate")
            print("id author ClassicGPT")
            print("uciok")
        elif line == "isready":
            print("readyok")
        elif line.startswith("ucinewgame"):
            board.reset()
            move_history.clear()
        elif line.startswith("position"):
            parts = line.split(" ")
            if "startpos" in parts:
                board.reset()
                if "moves" in parts:
                    for mv in parts[parts.index("moves")+1:]:
                        board.push_uci(mv)
                        move_history.append(chess.Move.from_uci(mv))
            elif "fen" in parts:
                fen_index = parts.index("fen")
                fen = " ".join(parts[fen_index + 1:fen_index + 7])
                board.set_fen(fen)
                if "moves" in parts:
                    for mv in parts[parts.index("moves")+1:]:
                        board.push_uci(mv)
                        move_history.append(chess.Move.from_uci(mv))
        elif line.startswith("go"):
            tokens = line.split()
            wtime = btime = None
            if "wtime" in tokens:
                wtime = int(tokens[tokens.index("wtime") + 1]) / 1000.0
            if "btime" in tokens:
                btime = int(tokens[tokens.index("btime") + 1]) / 1000.0
            time_left = wtime if board.turn == chess.WHITE else btime
            think_time = min(2.0, (time_left or 5.0) * 0.02)

            start = time.time()
            move = choose_move(board, think_time)
            elapsed = int((time.time() - start) * 1000)

            if move:
                board.push(move)
                move_history.append(move)
                score = evaluate_board(board, move_history)
                board.pop()
                move_history.pop()
                print(f"info score cp {score} time {elapsed}")
                print(f"bestmove {move.uci()}")
            else:
                print("bestmove 0000")
        elif line == "quit":
            break

        sys.stdout.flush()

if __name__ == "__main__":
    main()
