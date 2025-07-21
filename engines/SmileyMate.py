#!/usr/bin/env python3
import sys, chess, random, time, re

# ====== Параметры оценки ======
piece_values = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3, chess.ROOK:5, chess.QUEEN:9, chess.KING:0}
center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
PST = {  # пример: пешки
    chess.PAWN: [
        0,0,0,0,0,0,0,0,
        5,5,5,-5,-5,5,5,5,
        1,1,2,3,3,2,1,1,
        0.5,0.5,1,2.5,2.5,1,0.5,0.5,
        0,0,0,2,2,0,0,0,
        0.5,-0.5,-1,0,0,-1,-0.5,0.5,
        0.5,1,1,-2,-2,1,1,0.5,
        0,0,0,0,0,0,0,0
    ],
    # можно добавить PST для других фигур
}

def square_area(sq, r):
    f, rk = chess.square_file(sq), chess.square_rank(sq)
    return [chess.square(f+df,rk+dr)
            for df in range(-r,r+1) for dr in range(-r,r+1)
            if 0<=f+df<8 and 0<=rk+dr<8]

def is_passed_pawn(board, sq, color):
    f, rk = chess.square_file(sq), chess.square_rank(sq)
    for df in [-1,0,1]:
        f2 = f+df
        if 0<=f2<8:
            rng = range(rk+1,8) if color==chess.WHITE else range(rk-1,-1,-1)
            if any(board.piece_type_at(chess.square(f2, r))==chess.PAWN and board.color_at(chess.square(f2,r))!=color
                   for r in rng):
                return False
    return True

def king_danger(board, color):
    ks = board.king(color)
    if ks is None: return -9999
    d=0
    attackers = board.attackers(not color, ks)
    d -= len(attackers)*50
    f,rk = chess.square_file(ks), chess.square_rank(ks)
    for df in [-1,0,1]:
        for dr in [1,2]:
            r = rk+dr if color==chess.WHITE else rk-dr
            if 0<=f+df<8 and 0<=r<8:
                p = board.piece_at(chess.square(f+df,r))
                if not (p and p.piece_type==chess.PAWN and p.color==color):
                    d -= 10
    if board.fullmove_number>10 and ks in [chess.E1, chess.E8]:
        d -= 30
    center_files, center_ranks = [3,4],[3,4]
    if f in center_files and rk in center_ranks:
        d -= 40
    for sq in square_area(ks,1):
        p=board.piece_at(sq)
        if p and p.color==color:
            d += 5
    return d

def is_stupid_move(board, mv):
    if board.fullmove_number<=6:
        p=board.piece_at(mv.from_square)
        if p and p.piece_type in (chess.QUEEN, chess.KING):
            return True
    return False

def evaluate(board):
    if board.is_checkmate():
        return 10000 if board.turn==chess.BLACK else -10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    s=0
    # материал
    mat= sum((len(board.pieces(pt,chess.WHITE))-len(board.pieces(pt,chess.BLACK)))*val
             for pt,val in piece_values.items())
    s+=mat*100
    # безопасность короля
    s+=king_danger(board,chess.WHITE)
    s-=king_danger(board,chess.BLACK)
    # positional
    pos=0
    for color in (chess.WHITE,chess.BLACK):
        sign=1 if color==chess.WHITE else -1
        for pt,pst in PST.items():
            for sq in board.pieces(pt,color):
                idx = sq if color==chess.WHITE else chess.square_mirror(sq)
                pos+=sign*pst[idx]
    wm = len(list(board.generate_legal_moves(chess.WHITE)))
    bm = len(list(board.generate_legal_moves(chess.BLACK)))
    pos+=(wm-bm)*0.1
    for sq in center_squares:
        pos+=(len(board.attackers(chess.WHITE,sq))-len(board.attackers(chess.BLACK,sq)))*0.2
    def pawn_struct(color):
        score=0
        pawns=board.pieces(chess.PAWN,color)
        files=[chess.square_file(p) for p in pawns]
        for f,cnt in {f:files.count(f) for f in set(files)}.items():
            if cnt>1: score-=0.5*(cnt-1)
        for p in pawns:
            file=chess.square_file(p)
            if not any(chess.square_file(o) in (file-1,file+1) for o in pawns):
                score-=0.5
            if is_passed_pawn(board,p,color):
                score+=1.0
        return score
    pos+= pawn_struct(chess.WHITE)-pawn_struct(chess.BLACK)
    s+=pos
    return s

def minimax(board, depth, alpha, beta):
    if depth==0 or board.is_game_over():
        return evaluate(board)
    if board.turn==chess.WHITE:
        v=-1e9
        for mv in board.legal_moves:
            board.push(mv)
            v2=minimax(board,depth-1,alpha,beta)
            board.pop()
            v=max(v,v2); alpha=max(alpha,v2)
            if beta<=alpha: break
        return v
    else:
        v=1e9
        for mv in board.legal_moves:
            board.push(mv)
            v2=minimax(board,depth-1,alpha,beta)
            board.pop()
            v=min(v,v2); beta=min(beta,v2)
            if beta<=alpha: break
        return v

def choose_at_depth(board, depth):
    best=None
    score = -1e9 if board.turn==chess.WHITE else 1e9
    moves=[m for m in board.legal_moves if not is_stupid_move(board,m)]
    if not moves: moves=list(board.legal_moves)
    for mv in moves:
        board.push(mv)
        s=minimax(board,depth-1,-1e9,1e9)
        board.pop()
        if (board.turn==chess.WHITE and s>score) or (board.turn==chess.BLACK and s<score):
            score,s, best = s,s, mv
    return best, score

def choose_move(board, tm):
    best=None
    start=time.time()
    for depth in range(1,100):
        if time.time()-start>tm: break
        mv,sc=choose_at_depth(board,depth)
        if mv: best=mv
    return best

def main():
    board=chess.Board()
    while True:
        line=sys.stdin.readline()
        if not line: break
        line=line.strip()
        if line=="uci":
            print("id name SmileyMate v4"); print("id author Classic"); print("uciok")
        elif line=="isready":
            print("readyok")
        elif line.startswith("ucinewgame"):
            board.reset()
        elif line.startswith("position"):
            parts=line.split()
            if "startpos" in parts:
                board.reset()
                if "moves" in parts:
                    for m in parts[parts.index("moves")+1:]:
                        board.push_uci(m)
            elif "fen" in parts:
                i=parts.index("fen")
                board.set_fen(" ".join(parts[i+1:i+7]))
                if "moves" in parts:
                    for m in parts[parts.index("moves")+1:]:
                        board.push_uci(m)
        elif line.startswith("go"):
            wtime=btime=winc=binc=0
            for k in ("wtime","btime","winc","binc"):
                match=re.search(fr"{k} (\d+)",line)
                if match:
                    locals()[k]=int(match.group(1))/1000.0
            tm = wtime/40 if board.turn==chess.WHITE and wtime else btime/40 if btime else 0.5
            tm = max(0.05,tm)
            mv=choose_move(board,tm)
            if mv: print("bestmove",mv.uci())
            else: print("bestmove 0000")
        elif line=="quit":
            break
        sys.stdout.flush()

if __name__=="__main__":
    main()
