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
    chess.KING: 0
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
        0, 0, 0, 0, 0, 0, 0, 0,
    ],
    chess.QUEEN: [
        -20, -10, -10, -5, -5, -10, -10, -20,
        -10, 0, 0, 0, 0, 0, 0, -10,
        -10, 0, 5, 5, 5, 5, 0, -10,
        -5, 0, 5, 5, 5, 5, 0, -5,
        0, 0, 5, 5, 5, 5, 0, -5,
        -10, 5, 5, 5, 5, 5, 0, -10,
        -10, 0, 5, 0, 0, 0, 0, -10,
        -20, -10, -10, -5, -5, -10, -10, -20,
    ],
    chess.KING: [
        20, 30, 10, 0, 0, 10, 30, 20,
        20, 20, 0, 0, 0, 0, 20, 20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
    ]
}

center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
attack_unit = {chess.PAWN: 1, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 5}
transposition_table = {}

def evaluate_board(board):
    if board.is_checkmate():
        return -100000 if board.turn else 100000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for piece_type in piece_values:
        white = board.pieces(piece_type, chess.WHITE)
        black = board.pieces(piece_type, chess.BLACK)
        score += len(white) * piece_values[piece_type]
        score -= len(black) * piece_values[piece_type]

        table = piece_square_tables.get(piece_type)
        for sq in white:
            if table: score += table[sq]
        for sq in black:
            if table: score -= table[chess.square_mirror(sq)]

    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 10 if piece.color == chess.WHITE else -10

    score += mobility_score(board)
    score += pawn_structure(board)
    score += king_safety(board, chess.WHITE)
    score -= king_safety(board, chess.BLACK)

    return score

def mobility_score(board):
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        mobility = 0
        for pt in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
            for sq in board.pieces(pt, color):
                mobility += len(board.attacks(sq))
        score += mobility * (1 if color == chess.WHITE else -1)
    return score

def pawn_structure(board):
    score = 0
    for color in [chess.WHITE, chess.BLACK]:
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]
        for sq in pawns:
            file = chess.square_file(sq)
            rank = chess.square_rank(sq)
            if files.count(file) > 1:
                score -= 15 if color == chess.WHITE else -15
            if not any(f in files for f in [file - 1, file + 1]):
                score -= 20 if color == chess.WHITE else -20
            is_passed = True
            for f in [file - 1, file, file + 1]:
                if 0 <= f <= 7:
                    if color == chess.WHITE:
                        ranks_to_check = range(rank + 1, 8)
                    else:
                        ranks_to_check = range(0, rank)
                    for r in ranks_to_check:
                        sq_check = chess.square(f, r)
                        piece = board.piece_at(sq_check)
                        if piece == chess.Piece(chess.PAWN, not color):
                            is_passed = False
            if is_passed:
                score += 30 if color == chess.WHITE else -30
    return score

def king_safety(board, color):
    king_sq = board.king(color)
    danger = 0
    for attacker_sq in board.attackers(not color, king_sq):
        piece = board.piece_at(attacker_sq)
        if piece:
            danger += attack_unit.get(piece.piece_type, 1)
    return -danger * 10 if color == chess.WHITE else danger * 10

def order_moves(board, moves):
    def score_move(move):
        if board.is_capture(move):
            captured_piece = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if captured_piece and attacker:
                return 10 * piece_values[captured_piece.piece_type] - piece_values[attacker.piece_type]
        if board.gives_check(move):
            return 5
        return 0
    return sorted(moves, key=score_move, reverse=True)

def quiescence(board, alpha, beta):
    stand_pat = evaluate_board(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    for move in order_moves(board, board.legal_moves):
        if board.is_capture(move) or board.gives_check(move):
            board.push(move)
            score = -quiescence(board, -beta, -alpha)
            board.pop()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
    return alpha

def negamax(board, depth, alpha, beta, start_time, time_limit):
    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta)

    if time.time() - start_time > time_limit:
        raise TimeoutError()

    max_eval = -float('inf')
    moves = order_moves(board, board.legal_moves)
    for move in moves:
        board.push(move)
        try:
            eval = -negamax(board, depth - 1, -beta, -alpha, start_time, time_limit)
        except TimeoutError:
            board.pop()
            raise
        board.pop()

        if eval >= beta:
            return beta
        if eval > max_eval:
            max_eval = eval
        if eval > alpha:
            alpha = eval
    return max_eval

def select_move(board, max_depth, time_limit):
    best_move = None
    best_score = -float('inf')
    start_time = time.time()
    moves = order_moves(board, board.legal_moves)

    for move in moves:
        board.push(move)
        try:
            score = -negamax(board, max_depth - 1, -float('inf'), float('inf'), start_time, time_limit)
        except TimeoutError:
            board.pop()
            break
        board.pop()
        if score > best_score:
            best_score = score
            best_move = move
        if time.time() - start_time > time_limit:
            break
    return best_move if best_move else random.choice(list(board.legal_moves))

def parse_go_command(command):
    # Пример строки: go wtime 300000 btime 300000 winc 0 binc 0 movestogo 40
    tokens = command.strip().split()
    info = {}
    for i in range(len(tokens)):
        if tokens[i] in ('wtime', 'btime', 'winc', 'binc', 'movestogo'):
            try:
                info[tokens[i]] = int(tokens[i+1])
            except:
                info[tokens[i]] = 0
    return info

def main():
    board = chess.Board()
    max_depth = 3
    while True:
        line = sys.stdin.readline().strip()
        if line == 'uci':
            print('id name SmileyMate')
            print('id author Classic')
            print('uciok')
        elif line == 'isready':
            print('readyok')
        elif line.startswith('position'):
            if 'startpos' in line:
                board.set_fen(chess.STARTING_FEN)
                moves_str = line.split('moves ')[1] if 'moves ' in line else ''
                moves = moves_str.split()
                for move in moves:
                    board.push_uci(move)
            elif 'fen' in line:
                fen = line.split('fen ')[1].split(' moves')[0]
                board.set_fen(fen)
                if 'moves ' in line:
                    moves_str = line.split('moves ')[1]
                    moves = moves_str.split()
                    for move in moves:
                        board.push_uci(move)
        elif line.startswith('go'):
            go_info = parse_go_command(line)
            # Выбираем время для хода, например 10% от оставшегося времени или максимум 2 секунды
            if board.turn == chess.WHITE:
                time_left = go_info.get('wtime', 60000)
                inc = go_info.get('winc', 0)
            else:
                time_left = go_info.get('btime', 60000)
                inc = go_info.get('binc', 0)

            # Минимальное время хода 0.1 сек, максимум 2 сек или 10% от оставшегося времени
            allocated_time = max(0.1, min(2.0, (time_left / 1000) * 0.1 + inc / 1000))

            move = select_move(board, max_depth, allocated_time)
            print(f'bestmove {move.uci()}')
            sys.stdout.flush()
        elif line == 'quit':
            break

if __name__ == '__main__':
    main()
