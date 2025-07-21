#!/usr/bin/env python3
import sys
import chess
import chess.polyglot
import time

# Автор Classic, движок SmileyMate

class SmileyMateEngine:
    def __init__(self):
        self.board = chess.Board()

    def evaluate(self, board):
        # Простейшая оценка: считаем материал
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        eval = 0
        for piece_type in piece_values:
            eval += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
            eval -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]
        return eval if board.turn == chess.WHITE else -eval

    def negamax(self, board, depth, alpha, beta):
        if depth == 0 or board.is_game_over():
            return self.evaluate(board)

        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            score = -self.negamax(board, depth - 1, -beta, -alpha)
            board.pop()
            if score > max_eval:
                max_eval = score
            if max_eval > alpha:
                alpha = max_eval
            if alpha >= beta:
                break
        return max_eval

    def find_best_move(self, board, max_depth=3):
        best_move = None
        max_eval = -float('inf')
        alpha = -float('inf')
        beta = float('inf')
        for move in board.legal_moves:
            board.push(move)
            score = -self.negamax(board, max_depth - 1, -beta, -alpha)
            board.pop()
            if score > max_eval:
                max_eval = score
                best_move = move
            if max_eval > alpha:
                alpha = max_eval
        return best_move


def main():
    engine = SmileyMateEngine()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()

        if line == "uci":
            print("id name SmileyMate")
            print("id author Classic")
            print("uciok")
        elif line == "isready":
            print("readyok")
        elif line.startswith("position"):
            # position startpos moves e2e4 e7e5 ...
            if "startpos" in line:
                engine.board.reset()
                if "moves" in line:
                    moves_part = line.split("moves")[1].strip()
                    moves = moves_part.split()
                    for uci_move in moves:
                        move = chess.Move.from_uci(uci_move)
                        engine.board.push(move)
            elif "fen" in line:
                fen = line.split("fen")[1].strip()
                if "moves" in fen:
                    fen, moves_part = fen.split("moves")
                    fen = fen.strip()
                    moves = moves_part.strip().split()
                else:
                    moves = []
                engine.board.set_fen(fen)
                for uci_move in moves:
                    move = chess.Move.from_uci(uci_move)
                    engine.board.push(move)
        elif line.startswith("go"):
            # Простой поиск с фиксированной глубиной
            best_move = engine.find_best_move(engine.board, max_depth=3)
            if best_move is None:
                print("bestmove 0000")  # нет ходов
            else:
                print(f"bestmove {best_move.uci()}")
        elif line == "quit":
            break


if __name__ == "__main__":
    main()
