#include <iostream>
#include <string>
#include <vector>
#include <chrono>
#include <algorithm>
#include <cctype>
#include <limits>
#include <sstream>
#include <unordered_map>

// --- Простая доска и ход ---

enum Piece {
    EMPTY = 0,
    WP = 1, WN = 2, WB = 3, WR = 4, WQ = 5, WK = 6,
    BP = 7, BN = 8, BB = 9, BR = 10, BQ = 11, BK = 12
};

const int BOARD_SIZE = 64;

struct Move {
    int from;
    int to;
    int captured;
    int promotion;

    Move(int f, int t, int c = EMPTY, int p = EMPTY)
        : from(f), to(t), captured(c), promotion(p) {}

    std::string uci() const {
        std::string files = "abcdefgh";
        std::string res;
        res += files[from % 8];
        res += std::to_string(8 - from / 8);
        res += files[to % 8];
        res += std::to_string(8 - to / 8);
        if (promotion != EMPTY) {
            char pchar = 'q';
            switch (promotion) {
                case WQ: case BQ: pchar = 'q'; break;
                case WR: case BR: pchar = 'r'; break;
                case WB: case BB: pchar = 'b'; break;
                case WN: case BN: pchar = 'n'; break;
            }
            res += pchar;
        }
        return res;
    }
};

// --- Утилиты ---

inline bool is_white(int piece) { return piece >= WP && piece <= WK; }
inline bool is_black(int piece) { return piece >= BP && piece <= BK; }
inline bool is_opponent(int piece, bool white_to_move) {
    if (piece == EMPTY) return false;
    return white_to_move ? is_black(piece) : is_white(piece);
}
inline bool is_same_color(int piece, bool white_to_move) {
    if (piece == EMPTY) return false;
    return white_to_move ? is_white(piece) : is_black(piece);
}

// --- Класс доски ---

class Board {
public:
    int squares[64];
    bool white_to_move;
    bool white_can_castle_kingside;
    bool white_can_castle_queenside;
    bool black_can_castle_kingside;
    bool black_can_castle_queenside;
    int en_passant_square; // -1 если нет
    int halfmove_clock;
    int fullmove_number;

    Board() {
        reset();
    }

    void reset() {
        const int start_pos[64] = {
            BR, BN, BB, BQ, BK, BB, BN, BR,
            BP, BP, BP, BP, BP, BP, BP, BP,
            EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
            EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
            EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
            EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY,
            WP, WP, WP, WP, WP, WP, WP, WP,
            WR, WN, WB, WQ, WK, WB, WN, WR
        };
        for (int i = 0; i < 64; ++i) squares[i] = start_pos[i];
        white_to_move = true;
        white_can_castle_kingside = true;
        white_can_castle_queenside = true;
        black_can_castle_kingside = true;
        black_can_castle_queenside = true;
        en_passant_square = -1;
        halfmove_clock = 0;
        fullmove_number = 1;
    }

    // Установить позицию из FEN (ограниченная поддержка)
    bool set_fen(const std::string& fen) {
        // Простейший разбор: <pieces> <turn> <castling> <ep> <halfmove> <fullmove>
        std::istringstream ss(fen);
        std::string pieces, turn, castling, ep;
        int halfmove, fullmove;
        if (!(ss >> pieces >> turn >> castling >> ep >> halfmove >> fullmove)) {
            return false;
        }

        int idx = 0;
        for (char c : pieces) {
            if (c == '/') continue;
            if (isdigit(c)) {
                int empty = c - '0';
                for (int i = 0; i < empty; ++i) squares[idx++] = EMPTY;
            } else {
                int p = fen_char_to_piece(c);
                if (p == -1) return false;
                squares[idx++] = p;
            }
        }
        if (idx != 64) return false;

        white_to_move = (turn == "w");
        white_can_castle_kingside = castling.find('K') != std::string::npos;
        white_can_castle_queenside = castling.find('Q') != std::string::npos;
        black_can_castle_kingside = castling.find('k') != std::string::npos;
        black_can_castle_queenside = castling.find('q') != std::string::npos;

        if (ep == "-")
            en_passant_square = -1;
        else
            en_passant_square = algebraic_to_square(ep);

        halfmove_clock = halfmove;
        fullmove_number = fullmove;

        return true;
    }

    static int fen_char_to_piece(char c) {
        switch (c) {
            case 'P': return WP;
            case 'N': return WN;
            case 'B': return WB;
            case 'R': return WR;
            case 'Q': return WQ;
            case 'K': return WK;
            case 'p': return BP;
            case 'n': return BN;
            case 'b': return BB;
            case 'r': return BR;
            case 'q': return BQ;
            case 'k': return BK;
            default: return -1;
        }
    }

    static int algebraic_to_square(const std::string& s) {
        if (s.size() != 2) return -1;
        char file = s[0];
        char rank = s[1];
        if (file < 'a' || file > 'h') return -1;
        if (rank < '1' || rank > '8') return -1;
        int f = file - 'a';
        int r = 8 - (rank - '0');
        return r * 8 + f;
    }

    std::string square_to_algebraic(int sq) const {
        char file = 'a' + (sq % 8);
        char rank = '8' - (sq / 8);
        return std::string() + file + rank;
    }

    // TODO: реализовать генерацию ходов, проверку шаха, рокировок, взятия на проходе и т.п.
    // Для примера — реализуем очень ограниченную генерацию ходов пешек и коней для белых и черных
    // В реальном движке нужен полный генератор и проверка шаха.

    // Ключевой момент — нужна генерация всех легальных ходов
    std::vector<Move> generate_moves() const {
        std::vector<Move> moves;

        // Для демонстрации - генерация простых пешечных ходов и захватов без спец. правил и проверок
        for (int sq = 0; sq < 64; ++sq) {
            int piece = squares[sq];
            if (piece == EMPTY) continue;
            if (white_to_move && !is_white(piece)) continue;
            if (!white_to_move && !is_black(piece)) continue;

            if (piece == WP) {
                int forward = sq - 8;
                if (forward >= 0 && squares[forward] == EMPTY) {
                    moves.emplace_back(sq, forward);
                }
                // захваты
                if (forward - 1 >= 0 && is_black(squares[forward - 1])) {
                    moves.emplace_back(sq, forward - 1, squares[forward - 1]);
                }
                if (forward + 1 < 64 && (forward + 1) % 8 != 0 && is_black(squares[forward + 1])) {
                    moves.emplace_back(sq, forward + 1, squares[forward + 1]);
                }
            }
            else if (piece == BP) {
                int forward = sq + 8;
                if (forward < 64 && squares[forward] == EMPTY) {
                    moves.emplace_back(sq, forward);
                }
                if (forward - 1 >= 0 && is_white(squares[forward - 1])) {
                    moves.emplace_back(sq, forward - 1, squares[forward - 1]);
                }
                if (forward + 1 < 64 && (forward + 1) % 8 != 0 && is_white(squares[forward + 1])) {
                    moves.emplace_back(sq, forward + 1, squares[forward + 1]);
                }
            }

            // TODO: Добавить остальные фигуры и рокировки, взятия на проходе, превращения, шах и т.п.
        }

        return moves;
    }

    void make_move(const Move& m) {
        squares[m.to] = squares[m.from];
        squares[m.from] = EMPTY;
        white_to_move = !white_to_move;
        if (!white_to_move) ++fullmove_number;
        en_passant_square = -1; // упрощение
    }

    void unmake_move(const Move& m, int captured_piece) {
        squares[m.from] = squares[m.to];
        squares[m.to] = captured_piece;
        white_to_move = !white_to_move;
        if (white_to_move) --fullmove_number;
        // Восстановление ep и других состояний не реализовано
    }

    bool is_game_over() const {
        // Упрощенно
        return false;
    }
};

// --- Оценка позиции ---

int piece_value(int piece) {
    switch (piece) {
        case WP: case BP: return 100;
        case WN: case BN: return 320;
        case WB: case BB: return 330;
        case WR: case BR: return 500;
        case WQ: case BQ: return 900;
        case WK: case BK: return 20000;
        default: return 0;
    }
}

int evaluate(const Board& board) {
    int score = 0;
    for (int i = 0; i < BOARD_SIZE; ++i) {
        int p = board.squares[i];
        if (p == EMPTY) continue;
        int val = piece_value(p);
        if (is_white(p)) score += val;
        else score -= val;
    }
    return board.white_to_move ? score : -score;
}

// --- Поиск ---

int alphabeta(Board& board, int depth, int alpha, int beta,
              std::chrono::steady_clock::time_point end_time) {
    if (depth == 0 || board.is_game_over() ||
        std::chrono::steady_clock::now() > end_time) {
        return evaluate(board);
    }

    auto moves = board.generate_moves();
    if (moves.empty()) {
        // Мат или пат (упрощенно)
        return evaluate(board);
    }

    if (board.white_to_move) {
        int maxEval = std::numeric_limits<int>::min();
        for (auto& m : moves) {
            int captured = board.squares[m.to];
            board.make_move(m);
            int eval = alphabeta(board, depth - 1, alpha, beta, end_time);
            board.unmake_move(m, captured);
            if (eval > maxEval) maxEval = eval;
            if (maxEval > alpha) alpha = maxEval;
            if (beta <= alpha) break;
        }
        return maxEval;
    } else {
        int minEval = std::numeric_limits<int>::max();
        for (auto& m : moves) {
            int captured = board.squares[m.to];
            board.make_move(m);
            int eval = alphabeta(board, depth - 1, alpha, beta, end_time);
            board.unmake_move(m, captured);
            if (eval < minEval) minEval = eval;
            if (minEval < beta) beta = minEval;
            if (beta <= alpha) break;
        }
        return minEval;
    }
}

std::string choose_best_move(Board& board, int time_limit_ms) {
    using clock = std::chrono::steady_clock;
    auto start_time = clock::now();
    auto end_time = start_time + std::chrono::milliseconds(time_limit_ms);

    std::vector<Move> moves = board.generate_moves();
    if (moves.empty()) return "0000";

    Move best_move = moves[0];
    int best_score = board.white_to_move ? std::numeric_limits<int>::min() : std::numeric_limits<int>::max();

    for (auto& move : moves) {
        int captured = board.squares[move.to];
        board.make_move(move);
        int score = alphabeta(board, 3, std::numeric_limits<int>::min(), std::numeric_limits<int>::max(), end_time);
        board.unmake_move(move, captured);

        if (board.white_to_move) {
            if (score > best_score) {
                best_score = score;
                best_move = move;
            }
        } else {
            if (score < best_score) {
                best_score = score;
                best_move = move;
            }
        }
        if (clock::now() > end_time) break;
    }

    return best_move.uci();
}

// --- UCI интерфейс ---

int main() {
    Board board;
    std::string line;

    while (std::getline(std::cin, line)) {
        if (line == "uci") {
            std::cout << "id name SmileyMate\n";
            std::cout << "id author Classic\n";
            std::cout << "uciok\n";
        } else if (line == "isready") {
            std::cout << "readyok\n";
        } else if (line == "ucinewgame") {
            board.reset();
        } else if (line.substr(0, 8) == "position") {
            if (line.find("startpos") != std::string::npos) {
                board.reset();
                size_t moves_pos = line.find("moves");
                if (moves_pos != std::string::npos) {
                    std::istringstream iss(line.substr(moves_pos + 6));
                    std::string move_str;
                    while (iss >> move_str) {
                        // Очень упрощенная обработка ходов: только базовая
                        // TODO: Реализовать применение ходов из uci
                        // Пока - просто игнорим
                    }
                }
            } else {
                size_t fen_pos = line.find("fen");
                if (fen_pos != std::string::npos) {
                    size_t fen_start = fen_pos + 4;
                    size_t fen_end = line.find(" moves", fen_start);
                    std::string fen_str = (fen_end == std::string::npos) ?
                        line.substr(fen_start) : line.substr(fen_start, fen_end - fen_start);
                    board.set_fen(fen_str);

                    size_t moves_pos = line.find("moves", fen_end);
                    if (moves_pos != std::string::npos) {
                        std::istringstream iss(line.substr(moves_pos + 6));
                        std::string move_str;
                        while (iss >> move_str) {
                            // TODO: см. выше
                        }
                    }
                }
            }
        } else if (line.substr(0, 2) == "go") {
            // Для примера — 1.5 секунды на ход
            std::string bestmove = choose_best_move(board, 1500);
            std::cout << "bestmove " << bestmove << std::endl;
        } else if (line == "quit") {
            break;
        }
        std::cout.flush();
    }
    return 0;
}
