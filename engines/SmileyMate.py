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

def evaluate_board(board):
    # Мат — супер + для выигрывающей стороны, супер - для проигрывающей
    if board.is_checkmate():
        # Если ход черных и мат — значит белые выиграли и наоборот
        return 10000 if board.turn == chess.BLACK else -10000
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

def minimax(board, depth):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    legal_moves = list(board.legal_moves)
    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1)
            board.pop()
            if eval > max_eval:
                max_eval = eval
        return max_eval
    else:
        min_eval = float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1)
            board.pop()
            if eval < min_eval:
                min_eval = eval
        return min_eval

def choose_move(board):
    # Если первый ход в партии — берём случайный, чтобы не тормозить
    if board.fullmove_number == 1:
        return random.choice(list(board.legal_moves))

    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    best_moves = []

    for move in board.legal_moves:
        board.push(move)
        score = minimax(board, 2)  # глубина 2
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
            print("id name SmileyMate version 1.0.3")
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
               
