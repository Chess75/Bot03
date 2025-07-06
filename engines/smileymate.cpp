#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>
#include <limits>
#include <sstream>
#include <map>

using namespace std;

enum Color { WHITE, BLACK, NONE };
enum Piece { EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING };

struct Square {
    int index;
    Square(int idx) : index(idx) {}
    int file() const { return index % 8; }
    int rank() const { return index / 8; }
};

struct Move {
    int from;
    int to;
    char promotion;

    Move(int f, int t, char p = 0) : from(f), to(t), promotion(p) {}

    string uci() const {
        string s;
        s += 'a' + from % 8;
        s += '1' + from / 8;
        s += 'a' + to % 8;
        s += '1' + to / 8;
        if (promotion) s += tolower(promotion);
        return s;
    }
};

struct PieceOnBoard {
    Color color;
    Piece piece;
};

struct Board {
    PieceOnBoard board[64];
    Color side;

    Board() { set_start_position(); }

    void set_start_position() {
        const string start =
            "rnbqkbnr"
            "pppppppp"
            "        "
            "        "
            "        "
            "        "
            "PPPPPPPP"
            "RNBQKBNR";
        for (int i = 0; i < 64; ++i) {
            char c = start[i];
            if (c == ' ') {
                board[i] = { NONE, EMPTY };
            } else {
                board[i].color = isupper(c) ? WHITE : BLACK;
                switch (tolower(c)) {
                    case 'p': board[i].piece = PAWN; break;
                    case 'n': board[i].piece = KNIGHT; break;
                    case 'b': board[i].piece = BISHOP; break;
                    case 'r': board[i].piece = ROOK; break;
                    case 'q': board[i].piece = QUEEN; break;
                    case 'k': board[i].piece = KING; break;
                }
            }
        }
        side = WHITE;
    }

    void make_move(const Move& move) {
        board[move.to] = board[move.from];
        board[move.from] = { NONE, EMPTY };
        if (move.promotion) {
            board[move.to].piece = promotion_piece(move.promotion);
        }
        side = (side == WHITE ? BLACK : WHITE);
    }

    void undo_move(const Move& move, PieceOnBoard captured) {
        board[move.from] = board[move.to];
        board[move.to] = captured;
        side = (side == WHITE ? BLACK : WHITE);
    }

    Piece promotion_piece(char c) {
        switch (tolower(c)) {
            case 'q': return QUEEN;
            case 'r': return ROOK;
            case 'b': return BISHOP;
            case 'n': return KNIGHT;
        }
        return QUEEN;
    }

    vector<Move> legal_moves() const {
        vector<Move> moves;
        for (int i = 0; i < 64; ++i) {
            if (board[i].color != side) continue;
            switch (board[i].piece) {
                case PAWN: generate_pawn_moves(i, moves); break;
                case KNIGHT: generate_knight_moves(i, moves); break;
                default: break;
            }
        }
        return moves;
    }

    void generate_pawn_moves(int from, vector<Move>& moves) const {
        int dir = (side == WHITE) ? 8 : -8;
        int to = from + dir;
        if (in_board(to) && board[to].piece == EMPTY) {
            moves.emplace_back(from, to);
        }
    }

    void generate_knight_moves(int from, vector<Move>& moves) const {
        static const int offsets[] = { 15, 17, -15, -17, 10, -10, 6, -6 };
        for (int off : offsets) {
            int to = from + off;
            if (!in_board(to)) continue;
            if (board[to].color != side)
                moves.emplace_back(from, to);
        }
    }

    bool in_board(int sq) const {
        return 0 <= sq && sq < 64;
    }

    int evaluate() const {
        int val = 0;
        for (int i = 0; i < 64; ++i) {
            if (board[i].piece == EMPTY) continue;
            int score = 0;
            switch (board[i].piece) {
                case PAWN: score = 100; break;
                case KNIGHT: score = 300; break;
                case BISHOP: score = 330; break;
                case ROOK: score = 500; break;
                case QUEEN: score = 900; break;
                case KING: score = 10000; break;
                default: break;
            }
            val += (board[i].color == WHITE ? score : -score);
        }
        return val;
    }
};

int minimax(Board& board, int depth, int alpha, int beta, bool maximizing) {
    if (depth == 0) return board.evaluate();

    vector<Move> moves = board.legal_moves();
    if (moves.empty()) return board.evaluate();

    if (maximizing) {
        int best = -100000;
        for (auto& m : moves) {
            PieceOnBoard captured = board.board[m.to];
            board.make_move(m);
            best = max(best, minimax(board, depth - 1, alpha, beta, false));
            board.undo_move(m, captured);
            alpha = max(alpha, best);
            if (beta <= alpha) break;
        }
        return best;
    } else {
        int best = 100000;
        for (auto& m : moves) {
            PieceOnBoard captured = board.board[m.to];
            board.make_move(m);
            best = min(best, minimax(board, depth - 1, alpha, beta, true));
            board.undo_move(m, captured);
            beta = min(beta, best);
            if (beta <= alpha) break;
        }
        return best;
    }
}

Move find_best_move(Board& board, int depth) {
    vector<Move> moves = board.legal_moves();
    int best = -100000;
    Move best_move = moves[0];

    for (auto& m : moves) {
        PieceOnBoard captured = board.board[m.to];
        board.make_move(m);
        int eval = minimax(board, depth - 1, -100000, 100000, false);
        board.undo_move(m, captured);
        if (eval > best) {
            best = eval;
            best_move = m;
        }
    }
    return best_move;
}

int main() {
    ios::sync_with_stdio(false);
    string line;
    Board board;

    while (getline(cin, line)) {
        if (line == "uci") {
            cout << "id name SmileyMate\n";
            cout << "id author Classic\n";
            cout << "uciok\n";
        } else if (line == "isready") {
            cout << "readyok\n";
        } else if (line == "ucinewgame") {
            board.set_start_position();
        } else if (line.rfind("position", 0) == 0) {
            if (line.find("startpos") != string::npos) {
                board.set_start_position();
                size_t pos = line.find("moves");
                if (pos != string::npos) {
                    istringstream moves(line.substr(pos + 6));
                    string m;
                    while (moves >> m) {
                        int from = (m[0] - 'a') + (m[1] - '1') * 8;
                        int to = (m[2] - 'a') + (m[3] - '1') * 8;
                        char promo = m.length() > 4 ? m[4] : 0;
                        board.make_move(Move(from, to, promo));
                    }
                }
            }
        } else if (line.rfind("go", 0) == 0) {
            Move best = find_best_move(board, 2);
            cout << "bestmove " << best.uci() << endl;
        } else if (line == "quit") {
            break;
        }
    }
    return 0;
}
