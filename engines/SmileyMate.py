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

def king_safety(board, color):
    king_square = board.king(color)
    if king_square is None:
        return 0  # король съеден? Это уже мат или нонсенс

    enemy_color = not color
    danger_score = 0

    # Проверяем угрозы королю — сколько фигур атакуют короля и рядом
    king_zone = [king_square]
    # Добавим соседние клетки вокруг короля для оценки
    for sq in chess.SQUARES:
        if chess.square_distance(sq, king_square) == 1:
            king_zone.append(sq)

    for sq in king_zone:
        attackers = board.attackers(enemy_color, sq)
        danger_score += len(attackers) * 0.5  # штраф за каждую угрозу

    # Проверим наличие своих фигур рядом — бонус за защиту
    defenders = 0
    for sq in king_zone:
        piece = board.piece_at(sq)
        if piece and piece.color == color and piece.piece_type != chess.KING:
            defenders += 0.3  # небольшой бонус за защиту

    return defenders - danger_score  # чем выше — тем безопаснее король

def evaluate_board(board):
    if board.is_checkmate():
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

    # Добавляем безопасность короля
    score += king_safety(board, chess.WHITE)
    score -= king_safety(board, chess.BLACK)

    return score

def minimax(board, depth, alpha, beta, start_time, time_limit):
    if depth == 0 or board.is_game_over() or (time.time() - start_time) > time_limit:
        return evaluate_board(board)

    legal_moves = list(board.legal_moves)
    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, start_time, time_limit)
            board.pop()
            if eval > max_eval:
                max_eval = eval
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta, start_time, time_limit)
            board.pop()
            if eval < min_eval:
                min_eval = eval
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def choose_search_params(format_name):
    format_name = format_name.lower()
    if "bullet" in format_name:
        return 2, 0.5
    elif "blitz" in format_name:
        return 3, 1.5
    else:
        return 4, 3.0

def iterative_deepening(board, max_depth, time_limit):
    start_time = time.time()
    best_move = None
    for depth in range(1, max_depth + 1):
        best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
        moves_at_this_depth = []
        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, depth - 1, -float('inf'), float('inf'), start_time, time_limit)
            board.pop()
            if board.turn == chess.WHITE:
                if score > best_score:
                    best_score = score
                    moves_at_this_depth = [move]
                elif score == best_score:
                    moves_at_this_depth.append(move)
            else:
                if score < best_score:
                    best_score = score
                    moves_at_this_depth = [move]
                elif score == best_score:
                    moves_at_this_depth.append(move)

            if time.time() - start_time > time_limit:
                break

        if moves_at_this_depth:
            best_move = random.choice(moves_at_this_depth)

        if time.time() - start_time > time_limit:
            break

    return best_move

def choose_move(board, format_name="blitz"):
    if board.fullmove_number == 1:
        return random.choice(list(board.legal_moves))

    max_depth, time_limit = choose_search_params(format_name)
    move = iterative_deepening(board, max_depth, time_limit)
    return move

def main():
    board = chess.Board()
    format_name = "blitz"

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate version 1.0.5")
            print("id author Classic")
            print("uciok")
        elif line == "isready":
            print("readyok")
        elif line.startswith("ucinewgame"):
            board.reset()
        elif line.startswith("setoption"):
            parts = line.split()
            if len(parts) >= 5 and parts[1] == "name" and parts[2] == "Format":
                format_name = parts[4]
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
            move = choose_move(board, format_name)
            if move is not None:
                print("bestmove", move.uci())
            else:
                print("bestmove 0000")
        elif line == "quit":
            break

        sys.stdout.flush()

if __name__ == "__main__":
    main()

