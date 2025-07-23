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
        -50, -40, -30, -30, -30, -30, -40, -50
    ],
    chess.BISHOP: [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10, 5, 0, 0, 0, 0, 5, -10,
        -10, 10, 10, 10, 10, 10, 10, -10,
        -10, 0, 10, 10, 10, 10, 0, -10,
        -10, 5, 5, 10, 10, 5, 5, -10,
        -10, 0, 5, 10, 10, 5, 0, -10,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -20, -10, -10, -10, -10, -10, -10, -20
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
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        20, 20, 0, 0, 0, 0, 20, 20,
        20, 30, 10, 0, 0, 10, 30, 20
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

def is_open_file(board, file_index):
    for rank in range(8):
        square = chess.square(file_index, rank)
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN:
            return False
    return True

def is_half_open_file(board, file_index, color):
    for rank in range(8):
        square = chess.square(file_index, rank)
        piece = board.piece_at(square)
        if piece and piece.piece_type == chess.PAWN and piece.color == color:
            return False
    return True

def evaluate_pawn_structure(board, color):
    score = 0
    pawns = board.pieces(chess.PAWN, color)
    files = defaultdict(int)

    for square in pawns:
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        files[file] += 1

        # Изолированная пешка
        adjacent_files = [file - 1, file + 1]
        isolated = True
        for adj in adjacent_files:
            if 0 <= adj < 8 and board.pieces(chess.PAWN, color) & chess.BB_FILES[adj]:
                isolated = False
        if isolated:
            score -= 15

        # Связанная пешка
        for df in [-1, 1]:
            if 0 <= file + df < 8:
                diag_square = chess.square(file + df, rank - 1 if color == chess.WHITE else rank + 1)
                if board.piece_at(diag_square) and board.piece_at(diag_square).piece_type == chess.PAWN and board.piece_at(diag_square).color == color:
                    score += 10

        # Пешка на 7-й (белые) или 2-й (черные) - сильный пешечный фактор
        if (color == chess.WHITE and rank == 6) or (color == chess.BLACK and rank == 1):
            score += 20

    # Двойные пешки - штраф
    for file, count in files.items():
        if count > 1:
            score -= 10 * (count - 1)

    return score

def evaluate_board(board):
    if board.is_checkmate():
        return -999999 if board.turn else 999999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    eval_white = 0
    eval_black = 0

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is not None:
            value = piece_values[piece.piece_type]
            pst = piece_square_tables[piece.piece_type][square if piece.color == chess.WHITE else chess.square_mirror(square)]
            if piece.color == chess.WHITE:
                eval_white += value + pst
            else:
                eval_black += value + pst

    # Активность фигур: количество атакованных центральных полей
    for square in center_squares:
        attackers_white = board.attackers(chess.WHITE, square)
        attackers_black = board.attackers(chess.BLACK, square)
        eval_white += len(attackers_white) * 10
        eval_black += len(attackers_black) * 10

    # Оценка пешечной структуры
    eval_white += evaluate_pawn_structure(board, chess.WHITE)
    eval_black += evaluate_pawn_structure(board, chess.BLACK)

    # Безопасность короля (шраф за открытые линии вокруг короля)
    for color in [chess.WHITE, chess.BLACK]:
        king_square = board.king(color)
        if king_square is not None:
            for sq in square_area(king_square, 1):
                piece = board.piece_at(sq)
                if piece is None:
                    # Открытая клетка рядом с королем
                    if color == chess.WHITE:
                        eval_white -= 5
                    else:
                        eval_black -= 5
                elif piece.color != color:
                    # Вражеская фигура рядом с королем
                    if color == chess.WHITE:
                        eval_white -= 10
                    else:
                        eval_black -= 10

    return eval_white - eval_black if board.turn else eval_black - eval_white

def move_score(board, move):
    score = 0
    # Каптура фигуры - ценность фигуры взятой минус взятой фигуры (больше, если выгодно)
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim and attacker:
            score += piece_values[victim.piece_type] * 10 - piece_values[attacker.piece_type] * 9

    # Превращение пешки в ферзя
    if move.promotion:
        score += piece_values[chess.QUEEN] * 10

    # Ходы, которые угрожают центру
    if move.to_square in center_squares:
        score += 5

    # Если ход выводит фигуру на более активную позицию (по таблице)
    piece = board.piece_at(move.from_square)
    if piece:
        pst_before = piece_square_tables[piece.piece_type][move.from_square if piece.color == chess.WHITE else chess.square_mirror(move.from_square)]
        pst_after = piece_square_tables[piece.piece_type][move.to_square if piece.color == chess.WHITE else chess.square_mirror(move.to_square)]
        score += pst_after - pst_before

    # Избегать простых потерь: если после хода фигура будет атакована без защиты - минус
    board.push(move)
    attacked_squares = board.attacks(move.to_square)
    defenders = board.attackers(board.turn, move.to_square)
    attackers = board.attackers(not board.turn, move.to_square)
    piece_after_move = board.piece_at(move.to_square)
    # Если фигура теперь под атакой без защиты
    if piece_after_move and attackers and not defenders:
        score -= piece_values[piece_after_move.piece_type]
    board.pop()

    return score

def order_moves(board, moves):
    scored_moves = []
    for move in moves:
        scored_moves.append((move_score(board, move), move))
    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return [move for score, move in scored_moves]

def minimax(board, depth, alpha, beta, maximizing_player):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board), None

    legal_moves = list(board.legal_moves)
    legal_moves = order_moves(board, legal_moves)

    best_move = None
    if maximizing_player:
        max_eval = -999999
        for move in legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = 999999
        for move in legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move

def choose_move(board):
    depth = 3  # Можно увеличить, если позволяет время
    eval, move = minimax(board, depth, -999999, 999999, board.turn)
    if move is None:
        move = random.choice(list(board.legal_moves))
    return move

def main():
    board = chess.Board()
    while True:
        line = sys.stdin.readline().strip()
        if line == 'uci':
            print('id name NewChessEngine-ai')
            print('id author Classic')
            print('uciok')
        elif line == 'isready':
            print('readyok')
        elif line.startswith('position'):
            # пример: position startpos moves e2e4 e7e5
            parts = line.split()
            if 'startpos' in parts:
                board.set_fen(chess.STARTING_FEN)
                if 'moves' in parts:
                    idx = parts.index('moves')
                    moves = parts[idx+1:]
                    for m in moves:
                        board.push_uci(m)
            elif 'fen' in parts:
                idx = parts.index('fen')
                fen = ' '.join(parts[idx+1:idx+7])
                board.set_fen(fen)
                if 'moves' in parts:
                    idx = parts.index('moves')
                    moves = parts[idx+1:]
                    for m in moves:
                        board.push_uci(m)
            else:
                board.reset()
        elif line.startswith('go'):
            move = choose_move(board)
            print('bestmove', move.uci())
        elif line == 'quit':
            break
        else:
            pass

if __name__ == '__main__':
    main()
