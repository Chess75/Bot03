#!/usr/bin/env python3
import sys
import chess
import random
import time

# Значения фигур
piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}

# Таблицы позиционного значения фигур (Piece-square tables)
pst = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10,-20,-20, 10, 10,  5,
         5, -5,-10,  0,  0,-10, -5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5,  5, 10, 25, 25, 10,  5,  5,
        10, 10, 20, 30, 30, 20, 10, 10,
        50, 50, 50, 50, 50, 50, 50, 50,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    chess.ROOK: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    chess.KING: [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ]
}

pst_eg_king = [
    -50,-30,-30,-30,-30,-30,-30,-50,
    -30,-20,-10,-10,-10,-10,-20,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 30, 40, 40, 30,-10,-30,
    -30,-10, 20, 30, 30, 20,-10,-30,
    -30,-30,  0,  0,  0,  0,-30,-30,
    -50,-30,-30,-30,-30,-30,-30,-50
]

# TT флаги
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

TT = {}

def evaluate_board(board):
    if board.is_checkmate():
        return -99999 if board.turn else 99999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    phase = 0
    for piece_type in piece_values:
        wp = board.pieces(piece_type, chess.WHITE)
        bp = board.pieces(piece_type, chess.BLACK)
        score += (len(wp) - len(bp)) * piece_values[piece_type]
        for sq in wp:
            pst_table = pst[piece_type]
            score += pst_table[sq]
        for sq in bp:
            pst_table = pst[piece_type]
            score -= pst_table[chess.square_mirror(sq)]
        phase += len(wp) + len(bp)

    king_black = board.king(chess.BLACK)
    king_white = board.king(chess.WHITE)
    king_black_mirrored = chess.square_mirror(king_black)

    # Используем фазу для оценки позиции короля (окончание игры или нет)
    if phase < 12:
        score += pst_eg_king[king_white]
        score -= pst_eg_king[king_black_mirrored]
    else:
        score += pst[chess.KING][king_white]
        score -= pst[chess.KING][king_black_mirrored]

    return score if board.turn else -score

def minimax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board), None

    key = (board.zobrist_hash(), depth)

    if key in TT:
        tt_depth, tt_score, tt_flag, tt_move = TT[key]
        if tt_depth >= depth:
            if tt_flag == EXACT:
                return tt_score, tt_move
            elif tt_flag == LOWERBOUND and tt_score > alpha:
                alpha = max(alpha, tt_score)
            elif tt_flag == UPPERBOUND and tt_score < beta:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score, tt_move

    best_score = -float('inf')
    best_move = None

    # Сортировка ходов по захватам (примитивное move ordering)
    moves = sorted(board.legal_moves, key=lambda m: board.is_capture(m), reverse=True)

    for move in moves:
        board.push(move)
        score, _ = minimax(board, depth - 1, -beta, -alpha)
        score = -score
        board.pop()

        if score > best_score:
            best_score = score
            best_move = move
        alpha = max(alpha, score)
        if alpha >= beta:
            break

    # Записываем в TT
    if best_score <= alpha:
        flag = UPPERBOUND
    elif best_score >= beta:
        flag = LOWERBOUND
    else:
        flag = EXACT

    TT[key] = (depth, best_score, flag, best_move)
    return best_score, best_move

def choose_move(board, time_limit=2.0):
    start_time = time.time()
    best_move = None
    best_score = None

    for depth in range(1, 64):
        if time.time() - start_time > time_limit:
            break
        score, move = minimax(board, depth, -float('inf'), float('inf'))
        if move is not None:
            best_move = move
            best_score = score
        if time.time() - start_time > time_limit:
            break

    if best_move:
        print(f"info score cp {best_score}")
        return best_move
    else:
        return random.choice(list(board.legal_moves))

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
            TT.clear()
        elif line.startswith("position"):
            parts = line.split()
            if "startpos" in parts:
                board.reset()
                moves = parts[parts.index("moves") + 1:] if "moves" in parts else []
            elif "fen" in parts:
                idx = parts.index("fen")
                fen = " ".join(parts[idx + 1:idx + 7])
                board.set_fen(fen)
                moves = parts[parts.index("moves") + 1:] if "moves" in parts else []
            else:
                moves = []

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
            print(f"bestmove {move.uci()}")
            board.push(move)
        elif line == "quit":
            break
        sys.stdout.flush()

if __name__ == "__main__":
    main()
