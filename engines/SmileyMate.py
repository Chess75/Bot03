import chess
import time

class SmileyMateEngine:
    def __init__(self):
        self.tt = TranspositionTable()

    def select_move(self, board, remaining_time=10):
        max_time = min(remaining_time * 0.9, 2.0)
        return self.iterative_deepening(board, max_time)

    def iterative_deepening(self, board, max_time):
        start_time = time.time()
        best_move = None
        depth = 1
        while True:
            if time.time() - start_time > max_time:
                break
            move = self.search_root(board, depth)
            if move is not None:
                best_move = move
            depth += 1
        return best_move

    def search_root(self, board, depth):
        best_score = float('-inf')
        best_move = None
        for move in board.legal_moves:
            board.push(move)
            score = -self.search(board, depth - 1, float('-inf'), float('inf'))
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
        return best_move

    def search(self, board, depth, alpha, beta):
        if depth == 0 or board.is_game_over():
            return self.evaluate(board)

        board_hash = board.transposition_key()
        tt_entry = self.tt.lookup(board_hash, depth)
        if tt_entry is not None:
            return tt_entry.score

        max_score = float('-inf')
        for move in board.legal_moves:
            board.push(move)
            score = -self.search(board, depth - 1, -beta, -alpha)
            board.pop()

            if score > max_score:
                max_score = score
            if max_score > alpha:
                alpha = max_score
            if alpha >= beta:
                break

        self.tt.store(board_hash, depth, max_score)
        return max_score

    def evaluate(self, board):
        # Простая оценка: материал + безопасность короля
        material = self.material_balance(board)
        king_safety = self.king_safety(board)
        return material + king_safety

    def material_balance(self, board):
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0
        }
        score = 0
        for piece_type in piece_values:
            score += len(board.pieces(piece_type, board.turn)) * piece_values[piece_type]
            score -= len(board.pieces(piece_type, not board.turn)) * piece_values[piece_type]
        return score

    def king_safety(self, board):
        king_square = board.king(board.turn)
        enemy_color = not board.turn
        penalty = 0
        if king_square is None:
            return penalty

        king_file = chess.square_file(king_square)
        king_rank = chess.square_rank(king_square)

        # Проверяем все соседние клетки вокруг короля (восьминаправленные)
        for df in [-1, 0, 1]:
            for dr in [-1, 0, 1]:
                if df == 0 and dr == 0:
                    continue
                f = king_file + df
                r = king_rank + dr
                if 0 <= f <= 7 and 0 <= r <= 7:
                    sq = chess.square(f, r)
                    piece = board.piece_at(sq)
                    if piece and piece.color == enemy_color:
                        penalty -= 20
        return penalty


class TranspositionTable:
    def __init__(self):
        self.table = {}

    def lookup(self, key, depth):
        entry = self.table.get(key)
        if entry is not None and entry['depth'] >= depth:
            return entry
        return None

    def store(self, key, depth, score):
        self.table[key] = {'depth': depth, 'score': score}


def main():
    board = chess.Board()
    engine = SmileyMateEngine()

    while not board.is_game_over():
        move = engine.select_move(board, remaining_time=10)
        if move is None:
            break
        print(f"Engine plays: {move}")
        board.push(move)
        print(board)
        print()

if __name__ == "__main__":
    main()
