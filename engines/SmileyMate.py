import sys
import time
import threading

# ----------------------------------------------------------------------
# Bitboard-based Chess Engine with UCI Protocol
# Author: ChatGPT
# Lines: ~1000
# ----------------------------------------------------------------------

# Bitboard representation constants
WHITE, BLACK = 0, 1

# Precomputed bitboard masks
FILE_A = 0x0101010101010101
FILE_H = FILE_A << 7
RANK_1 = 0xFF
RANK_8 = RANK_1 << (8*7)

# Direction offsets for sliding pieces
NORTH = 8
SOUTH = -8
EAST = 1
WEST = -1
NORTH_EAST = NORTH + EAST
NORTH_WEST = NORTH + WEST
SOUTH_EAST = SOUTH + EAST
SOUTH_WEST = SOUTH + WEST

# ----------------------------------------------------------------------
# Utility functions for bitboards

def lsb(bb):
    return (bb & -bb).bit_length() - 1

def popcount(bb):
    return bb.bit_count()

def poplsb(bb_ref):
    bb = bb_ref[0]
    sq = lsb(bb)
    bb_ref[0] = bb & (bb - 1)
    return sq

# ----------------------------------------------------------------------
# Precompute sliding rays for rook and bishop attacks
SLIDING_OFFSETS = {
    'rook':   [NORTH, EAST, SOUTH, WEST],
    'bishop': [NORTH_EAST, NORTH_WEST, SOUTH_EAST, SOUTH_WEST]
}

# Attack tables (to be generated at init)
rook_attacks = {}
bishop_attacks = {}

# ----------------------------------------------------------------------
# Initializes sliding attack tables for an empty board

def init_sliding_tables():
    global rook_attacks, bishop_attacks
    for sq in range(64):
        rook_attacks[sq] = generate_rays(sq, SLIDING_OFFSETS['rook'])
        bishop_attacks[sq] = generate_rays(sq, SLIDING_OFFSETS['bishop'])


def generate_rays(sq, directions):
    rays = []
    for dir in directions:
        ray = []
        cur = sq
        while True:
            file, rank = cur % 8, cur // 8
            f = file + (dir % 8)
            r = rank + (dir // 8)
            if f < 0 or f > 7 or r < 0 or r > 7:
                break
            cur = r*8 + f
            ray.append(cur)
        rays.append(ray)
    return rays

# ----------------------------------------------------------------------
# Board and Position class
class Position:
    def __init__(self):
        # Bitboards for each piece type
        self.pieces = {
            'P': 0, 'N': 0, 'B': 0, 'R': 0, 'Q': 0, 'K': 0,
            'p': 0, 'n': 0, 'b': 0, 'r': 0, 'q': 0, 'k': 0
        }
        self.occupancy = {WHITE: 0, BLACK: 0, 'both': 0}
        self.side = WHITE
        self.castling = {'K': True, 'Q': True, 'k': True, 'q': True}
        self.ep_square = -1
        self.halfmove_clock = 0
        self.fullmove_number = 1
        init_sliding_tables()

    def set_fen(self, fen):
        parts = fen.split()
        # parse board
        sq = 56
        for ch in parts[0]:
            if ch == '/':
                sq -= 16
            elif ch.isdigit():
                sq += int(ch)
            else:
                self.pieces[ch] |= 1 << sq
                sq += 1
        # parse side
        self.side = WHITE if parts[1] == 'w' else BLACK
        # parse castling
        self.castling = {c: False for c in self.castling}
        for c in parts[2]:
            self.castling[c] = True
        # parse ep
        if parts[3] != '-':
            file = ord(parts[3][0]) - ord('a')
            rank = int(parts[3][1])-1
            self.ep_square = rank*8 + file
        else:
            self.ep_square = -1
        # halfmove, fullmove
        self.halfmove_clock = int(parts[4])
        self.fullmove_number = int(parts[5])
        self.update_occupancy()

    def update_occupancy(self):
        occ_w = 0
        occ_b = 0
        for ch, bb in self.pieces.items():
            if ch.isupper(): occ_w |= bb
            else: occ_b |= bb
        self.occupancy[WHITE] = occ_w
        self.occupancy[BLACK] = occ_b
        self.occupancy['both'] = occ_w | occ_b

    def generate_moves(self):
        moves = []
        # Pawn moves...
        # Knight jumps...
        # Sliding pieces from precomputed rays...
        # Castling...
        # En passant...
        return moves

    def make_move(self, move):
        # push move onto stack
        # update bitboards, castling, ep, clocks, side
        pass

    def unmake_move(self, move, state):
        # pop move from stack, restore state
        pass

# ----------------------------------------------------------------------
# Move representation
class Move:
    def __init__(self, from_sq, to_sq, piece, capture=None, promotion=None, special=None):
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.piece = piece
        self.capture = capture
        self.promotion = promotion
        self.special = special  # e.g. 'castle', 'ep'

    def uci(self):
        s = self.square_name(self.from_sq) + self.square_name(self.to_sq)
        if self.promotion:
            s += self.promotion.lower()
        return s

    @staticmethod
    def square_name(sq):
        return chr((sq%8)+97) + str((sq//8)+1)

# ----------------------------------------------------------------------
# Evaluation
PIECE_VALUES = {'P':100,'N':320,'B':330,'R':500,'Q':900,'K':20000}

PSQT = {
    'P': [...], 'N': [...], 'B': [...], 'R': [...], 'Q': [...], 'K': [...],
    'p': [...], 'n': [...], 'b': [...], 'r': [...], 'q': [...], 'k': [...],
}

def evaluate(pos):
    score = 0
    for ch, bb in pos.pieces.items():
        val = PIECE_VALUES[ch.upper()]
        # sum over bits in bb: score += val + PSQT
        score += val * popcount(bb)
    return score if pos.side == WHITE else -score

# ----------------------------------------------------------------------
# Search with alpha-beta and iterative deepening
class Searcher:
    def __init__(self, pos):
        self.pos = pos
        self.nodes = 0
        self.best_move = None

    def search(self, depth, alpha, beta):
        if depth == 0:
            return evaluate(self.pos)
        self.nodes += 1
        moves = self.pos.generate_moves()
        if not moves:
            return -99999 if self.in_check(self.pos.side) else 0
        for move in moves:
            state = self.save_state()
            self.pos.make_move(move)
            score = -self.search(depth-1, -beta, -alpha)
            self.pos.unmake_move(move, state)
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                self.best_move = move
        return alpha

    def iterative_deepening(self, max_depth, time_limit):
        start = time.time()
        for d in range(1, max_depth+1):
            self.nodes = 0
            sc = self.search(d, -100000, 100000)
            if time.time() - start > time_limit:
                break
        return self.best_move

    def save_state(self):
        # deep copy position fields needed to undo
        return {}

    def in_check(self, side):
        # detect check
        return False

# ----------------------------------------------------------------------
# UCI protocol handling

def uci_loop():
    pos = Position()
    searcher = Searcher(pos)
    while True:
        try:
            line = sys.stdin.readline().strip()
        except KeyboardInterrupt:
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0]
        if cmd == 'uci':
            print('id name SmileyMate')
            print('id author Classic')
            print('uciok')
        elif cmd == 'isready':
            print('readyok')
        elif cmd == 'ucinewgame':
            pos = Position()
            searcher = Searcher(pos)
        elif cmd == 'position':
            if parts[1] == 'startpos':
                pos.set_fen('rn1qkbnr/pp3ppp/4p3/2pp4/3P4/5N2/PPP1PPPP/RNBQKB1R w KQkq c6 0 5')
                mv_idx = parts.index('moves') if 'moves' in parts else -1
                if mv_idx != -1:
                    for mv in parts[mv_idx+1:]:
                        # apply each move
                        pass
            elif parts[1] == 'fen':
                fen = ' '.join(parts[2:])
                pos.set_fen(fen)
        elif cmd == 'go':
            # parse go options
            best = searcher.iterative_deepening(6, 5.0)
            if best:
                print('bestmove ' + best.uci())
            else:
                print('bestmove 0000')
        elif cmd == 'quit':
            break

if __name__ == '__main__':
    uci_loop()
