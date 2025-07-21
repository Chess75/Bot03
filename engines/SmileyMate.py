import chess
import chess.engine
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

class SimpleChessNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(12, 64, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(128*8*8, 256)
        self.fc2 = nn.Linear(256, 1)
    
    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.view(-1, 128*8*8)
        x = F.relu(self.fc1(x))
        return torch.tanh(self.fc2(x))

def board_to_tensor(board):
    piece_map = board.piece_map()
    planes = np.zeros((12, 8, 8), dtype=np.float32)
    piece_to_plane = {
        chess.PAWN: 0, chess.KNIGHT:1, chess.BISHOP:2,
        chess.ROOK:3, chess.QUEEN:4, chess.KING:5
    }
    for square, piece in piece_map.items():
        plane = piece_to_plane[piece.piece_type]
        if piece.color == chess.WHITE:
            planes[plane][square//8][square%8] = 1
        else:
            planes[plane+6][square//8][square%8] = 1
    return torch.tensor(planes).unsqueeze(0)  # batch 1

class SmileyMateEngine:
    def __init__(self, net, max_depth=3):
        self.net = net
        self.max_depth = max_depth

    def evaluate(self, board):
        # Нейросетевой прогноз позиции
        with torch.no_grad():
            tensor = board_to_tensor(board)
            score = self.net(tensor).item()
        return score

    def negamax(self, board, depth, alpha, beta, color):
        if depth == 0 or board.is_game_over():
            return color * self.evaluate(board)

        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = -self.negamax(board, depth-1, -beta, -alpha, -color)
            board.pop()

            if eval > max_eval:
                max_eval = eval
            if eval > alpha:
                alpha = eval
            if alpha >= beta:
                break
        return max_eval

    def find_best_move(self, board):
        best_move = None
        alpha = -float('inf')
        beta = float('inf')
        color = 1 if board.turn == chess.WHITE else -1

        for move in board.legal_moves:
            board.push(move)
            score = -self.negamax(board, self.max_depth-1, -beta, -alpha, -color)
            board.pop()
            if score > alpha:
                alpha = score
                best_move = move
        return best_move

if __name__ == "__main__":
    import sys
    board = chess.Board()
    net = SimpleChessNet()
    # Тут можно загрузить веса обученной нейросети (если есть)
    engine = SmileyMateEngine(net, max_depth=3)

    while not board.is_game_over():
        print(board)
        if board.turn == chess.WHITE:
            move = engine.find_best_move(board)
            print("Engine (White) move:", move)
        else:
            # Человеческий ход из stdin (для теста)
            user_move = input("Your move: ")
            move = chess.Move.from_uci(user_move)
            if move not in board.legal_moves:
                print("Illegal move!")
                continue
        board.push(move)

    print("Game over:", board.result())
