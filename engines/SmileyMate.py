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
    if board.is_checkmate():
        return 10000 if board.turn == chess.BLACK else -10000
    if board.is_stalemate():
        return 0

    score = 0

    # 1. Материал
    for piece_type in piece_values:
        score += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]

    # 2. Безопасность короля (штраф за открытый файл)
    for color in [chess.WHITE, chess.BLACK]:
        king_sq = board.king(color)
        if king_sq is not None:
            file = chess.square_file(king_sq)
            file_squares = [chess.square(file, rank) for rank in range(8)]
            open_file = all(board.piece_type_at(sq) != chess.PAWN for sq in file_squares)
            if open_file:
                score += -0.5 if color == chess.WHITE else 0.5

    # 3. Пешечная структура
    def pawn_structure_penalty(color):
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]
        penalties = 0
        for file in set(files):
            count = files.count(file)
            if count > 1:
                penalties += 0.25 * (count - 1)  # двойные
        for sq in pawns:
            file = chess.square_file(sq)
            adj_files = [file - 1, file + 1]
            has_adjacent = False
            for adj in adj_files:
                if 0 <= adj <= 7:
                    for rank in range(8):
                        if board.piece_at(chess.square(adj, rank)) == chess.Piece(chess.PAWN, color):
                            has_adjacent = True
                            break
            if not has_adjacent:
                penalties += 0.3  # изолированная
        return penalties

    score -= pawn_structure_penalty(chess.WHITE)
    score += pawn_structure_penalty(chess.BLACK)

    # Проходные пешки
    def passed_pawn_bonus(color):
        bonus = 0
        direction = 1 if color == chess.WHITE else -1
        pawns = board.pieces(chess.PAWN, color)
        enemy_pawns = board.pieces(chess.PAWN, not color)
        for sq in pawns:
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)
            blocked = False
            for step in range(1, 8):
                forward_rank = rank + step * direction
                if forward_rank < 0 or forward_rank > 7:
                    break
                for adj_file in [file - 1, file, file + 1]:
                    if 0 <= adj_file <= 7:
                        check_sq = chess.square(adj_file, forward_rank)
                        if check_sq in enemy_pawns:
                            blocked = True
                            break
                if blocked:
                    break
            if not blocked:
                bonus += 0.5
        return bonus

    score += passed_pawn_bonus(chess.WHITE)
    score -= passed_pawn_bonus(chess.BLACK)

    # 4. Центр
    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 0.2 if piece.color == chess.WHITE else -0.2

    # 5. Мобильность
    white_mob = len(list(board.legal_moves)) if board.turn == chess.WHITE else 0
    board.push(chess.Move.null())
    black_mob = len(list(board.legal_moves)) if board.turn == chess.BLACK else 0
    board.pop()
    score += 0.05 * white_mob - 0.05 * black_mob

    return score

def order_moves(board):
    def move_score(move):
        score = 0
        if board.is_capture(move):
            score += 10
        if board.gives_check(move):
            score += 5
        return score
    return sorted(board.legal_moves, key=move_score, reverse=True)

def alphabeta(board, depth, alpha, beta, maximizing_player):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    moves = order_moves(board)

    if maximizing_player:
        max_eval = -float('inf')
        for move in moves:
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
        for move in moves:
            board.push(move)
            eval = alphabeta(board, depth - 1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def choose_move(board):
    if board.fullmove_number == 1:
        return random.choice(list(board.legal_moves))

    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    best_moves = []

    for move in board.legal_moves:
        board.push(move)
        score = alphabeta(board, 3, -float('inf'), float('inf'), not board.turn)
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
            print("id name SmileyMate version 1.4")
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

               
