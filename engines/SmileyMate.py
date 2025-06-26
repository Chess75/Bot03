#!/usr/bin/env python3
import sys
import chess
import random

piece_values = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]

def evaluate_pawn_structure(board):
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]

        isolated_penalty = 0.2
        doubled_penalty = 0.2

        for f in set(files):
            count = files.count(f)
            if count > 1:
                penalty = -doubled_penalty * (count - 1)
                score += penalty if color == chess.WHITE else -penalty

            if (f - 1 not in files) and (f + 1 not in files):
                penalty = -isolated_penalty
                score += penalty if color == chess.WHITE else -penalty
    return score

def evaluate_board(board):
    if board.is_checkmate():
        return 10000 if board.turn == chess.BLACK else -10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # Материал
    for piece_type in piece_values:
        white_count = len(board.pieces(piece_type, chess.WHITE))
        black_count = len(board.pieces(piece_type, chess.BLACK))
        value = piece_values[piece_type]
        score += value * (white_count - black_count)

    # Активность (подвижность)
    white_moves = len(list(board.legal_moves)) if board.turn == chess.WHITE else 0
    board.push(chess.Move.null())
    black_moves = len(list(board.legal_moves)) if board.turn == chess.BLACK else 0
    board.pop()
    score += 0.1 * (white_moves - black_moves)

    # Пешечная структура
    score += evaluate_pawn_structure(board)

    # Центр
    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            bonus = 0.2
            score += bonus if piece.color == chess.WHITE else -bonus

    return score

def alphabeta(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    legal_moves = list(board.legal_moves)

    if maximizing:
        max_eval = -float('inf')
        for move in legal_moves:
            board.push(move)
            eval = alphabeta(board, depth - 1, alpha, beta, False)
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
            eval = alphabeta(board, depth - 1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def choose_move(board):
    # Первый ход — случайный для разнообразия
    if board.fullmove_number == 1:
        return random.choice(list(board.legal_moves))

    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    best_moves = []

    for move in board.legal_moves:
        board.push(move)
        score = alphabeta(board, depth=3, alpha=-float('inf'), beta=float('inf'), maximizing=(not board.turn))
        board.pop()

        if board.turn == chess.WHITE:
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)
        else:
            if score < best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

    return random.choice(best_moves) if best_moves else None

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate v1.0.4")
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

