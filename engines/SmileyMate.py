import chess
import chess.polyglot
import time

class TranspositionTable:
    def __init__(self):
        self.table = {}

    def store(self, zobrist_key, depth, score, flag, move):
        self.table[zobrist_key] = (depth, score, flag, move)

    def lookup(self, zobrist_key, depth):
        entry = self.table.get(zobrist_key)
        if entry and entry[0] >= depth:
            return entry
        return None

class OpeningBook:
    def __init__(self, path="data/book.bin"):
        try:
            self.book = chess.polyglot.open_reader(path)
        except Exception:
            self.book = None

    def get_move(self, board):
        if not self.book:
            return None
        try:
            entry = self.book.find(board)
            return entry.move
        except Exception:
            return None

class PawnStructureEvaluator:
    def __init__(self):
        self.isolated_penalty = -10
        self.doubled_penalty = -8
        self.passed_bonus = 20
        self.backward_penalty = -5

    def evaluate(self, board, color):
        score = 0
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(p) for p in pawns]

        # Isolated pawns
        for f in files:
            if not any((file == f-1 or file == f+1) for file in files):
                score += self.isolated_penalty

        # Doubled pawns
        for f in set(files):
            count = files.count(f)
            if count > 1:
                score += self.doubled_penalty * (count - 1)

        # Passed pawns
        for p in pawns:
            if self.is_passed_pawn(board, p, color):
                score += self.passed_bonus

        # Backward pawns — можно расширить при необходимости

        return score

    def is_passed_pawn(self, board, square, color):
        enemy_color = not color
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        if color == chess.WHITE:
            ahead_squares = [chess.square(f, r) for f in range(file - 1, file + 2)
                             for r in range(rank + 1, 8) if 0 <= f <= 7]
        else:
            ahead_squares = [chess.square(f, r) for f in range(file - 1, file + 2)
                             for r in range(0, rank) if 0 <= f <= 7]

        for sq in ahead_squares:
            if sq in board.pieces(chess.PAWN, enemy_color):
                return False
        return True

class MoveFilter:
    def __init__(self):
        pass

    def is_good_sacrifice(self, board, move):
        # Не допускаем простую потерю материала без компенсации
        if board.is_capture(move):
            after = board.copy()
            after.push(move)
            attackers = after.attackers(not after.turn, move.to_square)
            # Если после хода атакуют нашу фигуру и захваченная фигура по цене меньше, считаем плохим
            captured_piece = board.piece_at(move.to_square)
            moving_piece = board.piece_at(move.from_square)
            if attackers and captured_piece and moving_piece:
                if captured_piece.piece_type > moving_piece.piece_type:
                    return False
        return True

class Engine:
    def __init__(self):
        self.tt = TranspositionTable()
        self.book = OpeningBook()
        self.pawn_eval = PawnStructureEvaluator()
        self.move_filter = MoveFilter()
        self.nodes = 0
        self.max_depth = 4
        self.start_time = None
        self.time_limit = 1.0
        self.best_move = None

    def evaluate(self, board):
        material = self.material_eval(board)
        pawns_w = self.pawn_eval.evaluate(board, chess.WHITE)
        pawns_b = self.pawn_eval.evaluate(board, chess.BLACK)
        pawn_structure = pawns_w - pawns_b
        mobility = len(list(board.legal_moves)) if board.turn == chess.WHITE else -len(list(board.legal_moves))
        king_safety = self.king_safety(board)

        total_eval = material + pawn_structure + mobility + king_safety
        return total_eval if board.turn == chess.WHITE else -total_eval

    def material_eval(self, board):
        values = {
            chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
            chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0
        }
        white_score = 0
        black_score = 0
        for piece_type in values:
            white_score += len(board.pieces(piece_type, chess.WHITE)) * values[piece_type]
            black_score += len(board.pieces(piece_type, chess.BLACK)) * values[piece_type]
        return white_score - black_score

    def king_safety(self, board):
        king_square = board.king(board.turn)
        enemy_color = not board.turn
        penalty = 0
        if king_square is None:
            return 0  # Например, если шахматная позиция окончена
        for sq in chess.SquareSet(chess.square_ring(king_square)):
            piece = board.piece_at(sq)
            if piece and piece.color == enemy_color:
                penalty -= 20
        return penalty

    def search(self, board, depth, alpha, beta):
        if time.time() - self.start_time > self.time_limit:
            raise TimeoutError

        self.nodes += 1
        if depth == 0 or board.is_game_over():
            return self.evaluate(board)

        tt_entry = self.tt.lookup(board.zobrist_hash(), depth)
        if tt_entry:
            stored_depth, score, flag, move = tt_entry
            if flag == 'EXACT':
                return score
            elif flag == 'LOWERBOUND':
                alpha = max(alpha, score)
            elif flag == 'UPPERBOUND':
                beta = min(beta, score)
            if alpha >= beta:
                return score

        max_eval = float('-inf')
        best_move_local = None

        moves = list(board.legal_moves)
        moves.sort(key=lambda m: (board.is_capture(m), board.gives_check(m)), reverse=True)

        for move in moves:
            if not self.move_filter.is_good_sacrifice(board, move):
                continue

            board.push(move)
            try:
                score = -self.search(board, depth - 1, -beta, -alpha)
            except TimeoutError:
                board.pop()
                raise
            board.pop()

            if score > max_eval:
                max_eval = score
                best_move_local = move

            alpha = max(alpha, score)
            if alpha >= beta:
                break

        # Определение флага для хранения в таблице
        flag = 'EXACT'
        # Здесь надо поправить условие — alpha и beta на момент возврата могут измениться, 
        # поэтому используем входные alpha и beta в функцию (alpha_orig, beta_orig)
        # Но проще сохранить исходные alpha и beta в переменные перед циклом
        # Сделаю это:
        # (Внесу переменную alpha_orig, beta_orig)
        # Из-за этого немного поменяю код:
        # Сохраним alpha_orig и beta_orig в начале функции

        # Перенесём выше:
        # def search(self, board, depth, alpha, beta):
        #    alpha_orig, beta_orig = alpha, beta

        # Добавим это сейчас:

        # В начале функции:
        # alpha_orig, beta_orig = alpha, beta

        # Так что исправим функцию сейчас полностью ниже.

        # Правильный флаг:

        if max_eval <= alpha_orig:
            flag = 'UPPERBOUND'
        elif max_eval >= beta_orig:
            flag = 'LOWERBOUND'

        self.tt.store(board.zobrist_hash(), depth, max_eval, flag, best_move_local)

        if depth == self.max_depth:
            self.best_move = best_move_local

        return max_eval

    def iterative_deepening(self, board, max_time=1.0):
        self.start_time = time.time()
        self.time_limit = max_time
        self.best_move = None
        self.nodes = 0

        for depth in range(1, self.max_depth + 1):
            try:
                self.search(board, depth, float('-inf'), float('inf'))
            except TimeoutError:
                break

        return self.best_move

    def select_move(self, board, remaining_time):
        book_move = self.book.get_move(board)
        if book_move:
            return book_move

        if remaining_time < 6:
            self.max_depth = 3
        else:
            self.max_depth = 5

        return self.iterative_deepening(board, max_time=min(remaining_time * 0.9, 2.0))


# ----------- Исправленная функция search с alpha_orig, beta_orig -----------

def search(self, board, depth, alpha, beta):
    alpha_orig, beta_orig = alpha, beta

    if time.time() - self.start_time > self.time_limit:
        raise TimeoutError

    self.nodes += 1
    if depth == 0 or board.is_game_over():
        return self.evaluate(board)

    tt_entry = self.tt.lookup(board.zobrist_hash(), depth)
    if tt_entry:
        stored_depth, score, flag, move = tt_entry
        if flag == 'EXACT':
            return score
        elif flag == 'LOWERBOUND':
            alpha = max(alpha, score)
        elif flag == 'UPPERBOUND':
            beta = min(beta, score)
        if alpha >= beta:
            return score

    max_eval = float('-inf')
    best_move_local = None

    moves = list(board.legal_moves)
    moves.sort(key=lambda m: (board.is_capture(m), board.gives_check(m)), reverse=True)

    for move in moves:
        if not self.move_filter.is_good_sacrifice(board, move):
            continue

        board.push(move)
        try:
            score = -self.search(board, depth - 1, -beta, -alpha)
        except TimeoutError:
            board.pop()
            raise
        board.pop()

        if score > max_eval:
            max_eval = score
            best_move_local = move

        alpha = max(alpha, score)
        if alpha >= beta:
            break

    flag = 'EXACT'
    if max_eval <= alpha_orig:
        flag = 'UPPERBOUND'
    elif max_eval >= beta_orig:
        flag = 'LOWERBOUND'

    self.tt.store(board.zobrist_hash(), depth, max_eval, flag, best_move_local)

    if depth == self.max_depth:
        self.best_move = best_move_local

    return max_eval

# Чтобы использовать исправленную функцию, нужно заменить метод в Engine:
Engine.search = search

# ----------- Пример использования ------------

def main():
    board = chess.Board()
    engine = Engine()
    while not board.is_game_over():
        print(board)
        print("Thinking...")
        # Для теста считаем, что осталось 10 секунд
        move = engine.select_move(board, remaining_time=10)
        print(f"Engine plays: {move}")
        board.push(move)
        # Для демонстрации — выйдем после 20 ходов
        if board.fullmove_number > 20:
            break

if __name__ == "__main__":
    main()
