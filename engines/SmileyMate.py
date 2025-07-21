#!/usr/bin/env python3
import chess
import chess.engine
import chess.polyglot
import time

# Автор Classic
# Движок SmileyMate

piece_values = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Пример piece-square tables для белых фигур (простые, для демонстрации)
piece_square_tables = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 27, 27, 10,  5,  5,
         0,  0,  0, 25, 25,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-25,-25, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    # Можно добавить остальные, пока хватит
}

class SmileyMate:
    def __init__(self):
        self.transposition_table = {}
        self.nodes = 0

    def evaluate(self, board: chess.Board) -> int:
        """Улучшенная функция оценки позиции"""
        score = 0
        for piece_type in piece_values:
            white_pieces = board.pieces(piece_type, chess.WHITE)
            black_pieces = board.pieces(piece_type, chess.BLACK)
            score += piece_values[piece_type] * (len(white_pieces) - len(black_pieces))
            # PST
            if piece_type in piece_square_tables:
                pst = piece_square_tables[piece_type]
                for sq in white_pieces:
                    score += pst[sq]
                for sq in black_pieces:
                    score -= pst[chess.square_mirror(sq)]
        score += self.king_safety(board)
        score += self.center_control(board)
        score += self.pawn_structure(board)
        return score if board.turn == chess.WHITE else -score

    def king_safety(self, board: chess.Board) -> int:
        safety = 0
        for color in [chess.WHITE, chess.BLACK]:
            king_sq = board.king(color)
            if king_sq is None:
                continue
            attackers = board.attackers(not color, king_sq)
            safety -= 30 * len(attackers) * (1 if color == chess.WHITE else -1)
        return safety

    def center_control(self, board: chess.Board) -> int:
        center = [chess.D4, chess.D5, chess.E4, chess.E5]
        score = 0
        for sq in center:
            score += 15 * (len(board.attackers(chess.WHITE, sq)) - len(board.attackers(chess.BLACK, sq)))
        return score

    def pawn_structure(self, board: chess.Board) -> int:
        score = 0
        for color in [chess.WHITE, chess.BLACK]:
            pawns = list(board.pieces(chess.PAWN, color))
            files = [chess.square_file(sq) for sq in pawns]
            isolated = [f for f in files if files.count(f) == 1 and
                        (f == 0 or files.count(f - 1) == 0) and
                        (f == 7 or files.count(f + 1) == 0)]
            double_pawns = [f for f in set(files) if files.count(f) > 1]
            penalty = -20 * len(isolated) - 15 * len(double_pawns)
            score += penalty if color == chess.WHITE else -penalty
        return score

    def quiescence(self, board: chess.Board, alpha: int, beta: int) -> int:
        stand_pat = self.evaluate(board)
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        for move in board.legal_moves:
            if board.is_capture(move):
                board.push(move)
                score = -self.quiescence(board, -beta, -alpha)
                board.pop()

                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
        return alpha

    def negamax(self, board: chess.Board, depth: int, alpha: int, beta: int) -> int:
        self.nodes += 1
        if depth == 0 or board.is_game_over():
            return self.quiescence(board, alpha, beta)

        board_hash = board.zobrist_hash()
        if board_hash in self.transposition_table:
            tt_depth, tt_value = self.transposition_table[board_hash]
            if tt_depth >= depth:
                return tt_value

        max_eval = -999999
        for move in board.legal_moves:
            board.push(move)
            eval = -self.negamax(board, depth - 1, -beta, -alpha)
            board.pop()

            if eval > max_eval:
                max_eval = eval
            if max_eval > alpha:
                alpha = max_eval
            if alpha >= beta:
                break

        self.transposition_table[board_hash] = (depth, max_eval)
        return max_eval

    def find_best_move(self, board: chess.Board, max_time=2.0):
        best_move = None
        start = time.time()
        depth = 1
        best_score = -999999

        while True:
            self.nodes = 0
            current_best_move = None
            alpha = -999999
            beta = 999999
            for move in board.legal_moves:
                board.push(move)
                score = -self.negamax(board, depth - 1, -beta, -alpha)
                board.pop()
                if score > best_score:
                    best_score = score
                    current_best_move = move
                if score > alpha:
                    alpha = score
            if current_best_move is not None:
                best_move = current_best_move
            if time.time() - start > max_time:
                break
            depth += 1

        return best_move

if __name__ == "__main__":
    board = chess.Board()
    engine = SmileyMate()

    while not board.is_game_over():
        print(board)
        if board.turn == chess.WHITE:
            print("Classic (SmileyMate) thinking...")
            move = engine.find_best_move(board, max_time=1.0)
        else:
            print("Waiting for opponent move...")
            # Тут можно заменить на ход из ввода или другого движка
            moves = list(board.legal_moves)
            move = moves[0]  # Для теста просто первый ход
        print("Best move:", move)
        board.push(move)
    print("Game over:", board.result())
