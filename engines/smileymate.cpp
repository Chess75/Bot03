#include <iostream>
#include <string>
#include <sstream>
#include <vector>
#include <map>
#include <limits>
#include <random>
#include <algorithm>
#include "uci_board.hpp" // Включает минимальную реализацию доски и правил

int evaluate(const Board& board) {
    if (board.is_checkmate())
        return board.side_to_move() == WHITE ? -10000 : 10000;
    if (board.is_stalemate())
        return 0;

    int score = 0;
    for (int sq = 0; sq < 64; ++sq) {
        Piece p = board.at(sq);
        if (p == EMPTY) continue;
        int value = 0;
        switch (p.type()) {
            case PAWN: value = 100; break;
            case KNIGHT: value = 320; break;
            case BISHOP: value = 330; break;
            case ROOK: value = 500; break;
            case QUEEN: value = 900; break;
            case KING: value = 0; break;
        }
        score += (p.color() == WHITE ? value : -value);
    }
    return score;
}

int minimax(Board& board, int depth, bool maximizing) {
    if (depth == 0 || board.is_game_over())
        return evaluate(board);

    int best = maximizing ? std::numeric_limits<int>::min() : std::numeric_limits<int>::max();
    auto moves = board.legal_moves();

    for (auto move : moves) {
        board.push(move);
        int eval = minimax(board, depth - 1, !maximizing);
        board.pop();
        if (maximizing)
            best = std::max(best, eval);
        else
            best = std::min(best, eval);
    }
    return best;
}

std::string find_best_move(Board& board, int depth) {
    int best_score = std::numeric_limits<int>::min();
    std::vector<std::string> best_moves;
    auto moves = board.legal_moves();

    for (auto move : moves) {
        board.push(move);
        int score = minimax(board, depth - 1, false);
        board.pop();

        if (score > best_score) {
            best_score = score;
            best_moves.clear();
            best_moves.push_back(move.uci());
        } else if (score == best_score) {
            best_moves.push_back(move.uci());
        }
    }

    if (best_moves.empty()) return "0000";
    return best_moves[rand() % best_moves.size()];
}

int main() {
    std::ios::sync_with_stdio(false);
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
            board.set_start_position();
        } else if (line.rfind("position", 0) == 0) {
            std::istringstream iss(line);
            std::string token, pos_type;
            iss >> token >> pos_type;
            if (pos_type == "startpos") {
                board.set_start_position();
            } else if (pos_type == "fen") {
                std::string fen, t;
                for (int i = 0; i < 6; ++i) {
                    iss >> t;
                    fen += t + " ";
                }
                board.set_fen(fen);
            }
            while (iss >> token) {
                if (token == "moves") continue;
                board.push_uci(token);
            }
        } else if (line.rfind("go", 0) == 0) {
            std::string move = find_best_move(board, 3);
            std::cout << "bestmove " << move << "\n";
        } else if (line == "quit") {
            break;
        }
    }

    return 0;
}
