#!/usr/bin/env python3
import sys
import chess
import random
import time

# Базовые значения фигур
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
    # Мат — очень важный фактор
    if board.is_checkmate():
        return 10000 if board.turn == chess.BLACK else -10000
    if board.is_stalemate():
        return 0

    score = 0

    # Материал
    for piece_type in piece_values:
        score += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]

    # Контроль центра
    for square in center_squares:
        piece = board.piece_at(square)
        if piece:
            score += 0.2 if piece.color == chess.WHITE else -0.2

    # Безопасность короля (простая оценка)
    def king_safety(color):
        king_square = board.king(color)
        if king_square is None:
            return -1000  # Король съеден или нет на доске
        # Проверка наличия фигур вокруг короля
        safety_score = 0
        for neighbor in chess.SquareSet(chess.square_ring(king_square)):
            piece = board.piece_at(neighbor)
            if piece and piece.color == color and piece.piece_type != chess.KING:
                safety_score += 0.1
        return safety_score

    score += king_safety(chess.WHITE) - king_safety(chess.BLACK)

    # Развитие фигур (более активные позиции)
    def development_score(color):
        development = 0
        for square in range(64):
            piece = board.piece_at(square)
            if piece and piece.color == color and piece.piece_type != chess.KING:
                # Фигуры вне начальных линий считаются более развитыми
                rank = square // 8
                if (color == chess.WHITE and rank > 1) or (color == chess.BLACK and rank < 6):
                    development += 0.05
        return development

    score += development_score(chess.WHITE) - development_score(chess.BLACK)

    return score

# Минимакс с альфа-бета отсечением для скорости
def minimax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    legal_moves = list(board.legal_moves)

    if board.turn == chess.WHITE:
        max_eval = -float('inf')
        for move in legal_moves:
            board.push(move)
            eval = minimax(board, depth - 1, alpha, beta)
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
            eval = minimax(board, depth - 1, alpha, beta)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

# Динамическая настройка глубины по времени или контролю времени (примерно)
def get_search_depth(time_left):
    if time_left < 5:
        return 2  # максимально быстрое решение для короткого времени
    elif time_left < 10:
        return 3
    elif time_left < 20:
        return 4
    else:
        return 5

def choose_move(board, time_left=20):
    depth = get_search_depth(time_left)

    best_score = -float('inf') if board.turn == chess.WHITE else float('inf')
    best_moves = []

    for move in list(board.legal_moves):
        start_time = time.time()
        board.push(move)
        score = minimax(board, depth -1 , -float('inf'), float('inf'))
        board.pop()

        elapsed_time = time.time() - start_time

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
    
    # Предположим контроль времени для примера (можно получать из командной строки или UCI протокола)
    total_time_seconds = 60 * 5  # например всего на партию
    
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
                    moves_list = parts[moves_index +1:]
                    for mv in moves_list:
                        try:
                            board.push_uci(mv)
                        except Exception as e:
                            pass
            elif "fen" in parts:
                fen_index= parts.index("fen")
                fen_str= " ".join(parts[fen_index+1: fen_index+7])
                try:
                    board.set_fen(fen_str)
                except Exception as e:
                    pass
                
                if "moves" in parts:
                    moves_index= parts.index("moves")
                    moves_list= parts[moves_index+1:]
                    for mv in moves_list:
                        try:
                            board.push_uci(mv)
                        except Exception as e:
                            pass
                
                
        
        elif line.startswith("go"):
            # Можно передавать оставшееся время сюда для динамики поиска.
            move= choose_move(board, total_time_seconds)
            if move is not None:
                print("bestmove", move.uci())
            else:
                print("bestmove 0000")
        
        elif line=="quit":
            break
        
        
        sys.stdout.flush()

if __name__=="__main__":
    main()
