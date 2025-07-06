// smileymate.cpp — self-contained UCI chess engine in C++
#include <bits/stdc++.h>
using namespace std;

// --- Constants and enums ---
enum Color { WHITE, BLACK, NO_COLOR };
enum Piece { EMPTY, WP, WN, WB, WR, WQ, WK, BP, BN, BB, BR, BQ, BK };

// Board state
struct Board {
    int sq[64];
    Color turn;
    bool wk, wq, bk, bq;
    int ep; // -1 if none
    // constructor
    Board() { reset(); }
    void reset() {
        const int init[64] = {
            BR,BN,BB,BQ,BK,BB,BN,BR,
            BP,BP,BP,BP,BP,BP,BP,BP,
            0,0,0,0,0,0,0,0,
            0,0,0,0,0,0,0,0,
            0,0,0,0,0,0,0,0,
            0,0,0,0,0,0,0,0,
            WP,WP,WP,WP,WP,WP,WP,WP,
            WR,WN,WB,WQ,WK,WB,WN,WR
        };
        memcpy(sq, init, sizeof(sq));
        turn=WHITE; wk=wq=bk=bq=true; ep=-1;
    }
    int piece(int i) const { return sq[i]; }
    bool in_board(int i) const { return i>=0 && i<64; }
    bool is_white(int p) const { return p>=WP && p<=WK; }
    bool is_black(int p) const { return p>=BP && p<=BK; }
};

// Convert index to UCI string
string uci(int from, int to, int promo=0){
    string s;
    s += char('a'+from%8);
    s += char('1'+from/8);
    s += char('a'+to%8);
    s += char('1'+to/8);
    if(promo){
        s += string("nbrq")[promo-2];
    }
    return s;
}

// Generate pseudo-legal moves (no checks), full moveset
void gen_moves(const Board &b, vector<string> &out){
    static const int knight_dirs[]={15,17,10,-10,6,-6,-17,-15};
    static const int bishop_dirs[]={9,7,-9,-7};
    static const int rook_dirs[]={8,-8,1,-1};
    static const int queen_dirs[]={9,7,-9,-7,8,-8,1,-1};

    int dir= (b.turn==WHITE?1:-1);
    for(int i=0;i<64;i++){
        int p=b.sq[i];
        if(p==EMPTY) continue;
        bool isWhite=(b.turn==WHITE ? b.is_white(p) : b.is_black(p));
        if(!isWhite) continue;
        if(p==WP || p==BP){
            int to=i+dir*8;
            if(b.in_board(to) && b.sq[to]==EMPTY)
                if((to<8||to>=56)){ // promotion rank
                    for(int promo=WN;promo<=WQ;promo++)
                        out.push_back(uci(i,to,promo));
                } else out.push_back(uci(i,to));
            // capture
            for(int dx:{-1,1}){
                int c=i+dir*8+dx;
                if(b.in_board(c) && b.sq[c]!=EMPTY){
                    bool opp=b.turn==WHITE?b.is_black(b.sq[c]):b.is_white(b.sq[c]);
                    if(opp){
                        if(to<8||to>=56){
                            for(int promo=WN;promo<=WQ;promo++)
                                out.push_back(uci(i,c,promo));
                        }else out.push_back(uci(i,c));
                    }
                }
            }
            // ep capture
            if(b.ep>=0){
                int ep_rank=b.ep/8;
                int i_rank=i/8;
                if(ep_rank==i_rank+dir){
                    for(int dx:{-1,1}){
                        if(i+dx==b.ep-(-dir*8)){
                            out.push_back(uci(i,b.ep));
                        }
                    }
                }
            }
        }
        else if(p==WN||p==BN){
            for(int d:knight_dirs){
                int to=i+d;
                if(!b.in_board(to)) continue;
                if(b.sq[to]==EMPTY ||
                   (b.turn==WHITE?b.is_black(b.sq[to]):b.is_white(b.sq[to])))
                   out.push_back(uci(i,to));
            }
        }
        else if(p==WB||p==BB||p==WR||p==BR||p==WQ||p==BQ){
            const int *dirs; int cnt;
            if(p==WB||p==BB){dirs=bishop_dirs;cnt=4;}
            else if(p==WR||p==BR){dirs=rook_dirs;cnt=4;}
            else {dirs=queen_dirs;cnt=8;}
            for(int k=0;k<cnt;k++){
                int d=dirs[k], to=i+d;
                while(b.in_board(to)){
                    if(b.sq[to]==EMPTY){
                        out.push_back(uci(i,to));
                    } else {
                        bool opp=b.turn==WHITE?b.is_black(b.sq[to]):b.is_white(b.sq[to]);
                        if(opp) out.push_back(uci(i,to));
                        break;
                    }
                    to+=d;
                }
            }
        }
        else if(p==WK||p==BK){
            for(int d:queen_dirs){
                int to=i+d;
                if(!b.in_board(to))continue;
                if(b.sq[to]==EMPTY ||
                   (b.turn==WHITE?b.is_black(b.sq[to]):b.is_white(b.sq[to])))
                    out.push_back(uci(i,to));
            }
            // castling - simplified: no check condition
            if(p==WK && i==4){
                if(b.wk && b.sq[5]==EMPTY && b.sq[6]==EMPTY)
                    out.push_back("e1g1");
                if(b.wq && b.sq[3]==EMPTY && b.sq[2]==EMPTY && b.sq[1]==EMPTY)
                    out.push_back("e1c1");
            } else if(p==BK && i==60){
                if(b.bk && b.sq[61]==EMPTY && b.sq[62]==EMPTY)
                    out.push_back("e8g8");
                if(b.bq && b.sq[59]==EMPTY && b.sq[58]==EMPTY && b.sq[57]==EMPTY)
                    out.push_back("e8c8");
            }
        }
    }
}

// Make move & undo
struct State { int captured, ep; bool wk,wq,bk,bq; };
void make_move(Board &b, const string &uci, State &st){
    int from=(uci[0]-'a') + (uci[1]-'1')*8;
    int to=(uci[2]-'a') + (uci[3]-'1')*8;
    st.captured=b.sq[to]; st.ep=b.ep;
    st.wk=b.wk; st.wq=b.wq;
    st.bk=b.bk; st.bq=b.bq;
    // castling adjustment
    if(b.sq[from]==WK && uci=="e1g1"){ b.sq[7]=EMPTY; b.sq[5]=WR; }
    if(b.sq[from]==WK && uci=="e1c1"){ b.sq[0]=EMPTY; b.sq[3]=WR; }
    if(b.sq[from]==BK && uci=="e8g8"){ b.sq[63]=EMPTY; b.sq[61]=BR; }
    if(b.sq[from]==BK && uci=="e8c8"){ b.sq[56]=EMPTY; b.sq[59]=BR; }
    // en passant
    if((b.sq[from]==WP||b.sq[from]==BP) && to==b.ep){
        int dir=(b.sq[from]==WP? -8:8);
        b.sq[to+dir] = EMPTY;
    }
    // promotion
    if(uci.size()==5){
        int promo=" nbrq"[uci[4]-'a'];
        b.sq[to]= (b.turn==WHITE?promo:promo+6);
    } else {
        b.sq[to]=b.sq[from];
    }
    b.sq[from]=EMPTY;
    // castling rights reset
    if(from==4) b.wk=b.wq=false;
    if(from==0) b.wq=false;
    if(from==7) b.wk=false;
    if(from==60) b.bk=b.bq=false;
    if(from==56) b.bq=false;
    if(from==63) b.bk=false;
    // ep
    b.ep=-1;
    if((b.sq[to]==WP && to-from==16) || (b.sq[to]==BP && from-to==16))
        b.ep = (from+to)/2;
    b.turn= (b.turn==WHITE?BLACK:WHITE);
}

void undo_move(Board &b, const string &uci, State &st){
    int from=(uci[0]-'a') + (uci[1]-'1')*8;
    int to=(uci[2]-'a') + (uci[3]-'1')*8;
    b.turn= (b.turn==WHITE?BLACK:WHITE);
    b.ep=st.ep; b.wk=st.wk; b.wq=st.wq; b.bk=st.bk; b.bq=st.bq;
    b.sq[from]=b.sq[to];
    b.sq[to]=st.captured;
    // undo castle rook
    if(uci=="e1g1"){ b.sq[5]=EMPTY; b.sq[7]=WR; }
    if(uci=="e1c1"){ b.sq[3]=EMPTY; b.sq[0]=WR; }
    if(uci=="e8g8"){ b.sq[61]=EMPTY; b.sq[63]=BR; }
    if(uci=="e8c8"){ b.sq[59]=EMPTY; b.sq[56]=BR; }
    // undo promo
    if(uci.size()==5){
        b.sq[from] = (b.turn==WHITE?WP:BP);
    }
}

// Simple evaluation
int eval(const Board &b){
    static int val[]={0,100,320,330,500,900,10000,100,320,330,500,900,10000};
    int s=0;
    for(int i=0;i<64;i++){
        s+=(b.sq[i]?((b.sq[i]<=6)?val[b.sq[i]]:-val[b.sq[i]]):0);
    }
    return (b.turn==WHITE)?s:-s;
}

// Alpha-beta with fixed depth
int dfs(Board &b, int depth, int alpha, int beta){
    if(depth==0) return eval(b);
    vector<string> moves;
    gen_moves(b,moves);
    if(moves.empty()) return eval(b);
    for(auto &m:moves){
        State st;
        make_move(b,m,st);
        int sc=-dfs(b,depth-1,-beta,-alpha);
        undo_move(b,m,st);
        if(sc>=beta)return beta;
        alpha=max(alpha,sc);
    }
    return alpha;
}

// Search best move at depth 3
string search(Board &b){
    vector<string> moves;
    gen_moves(b,moves);
    int best=-1e9; string bestm="0000";
    for(auto &m:moves){
        State st;
        make_move(b,m,st);
        int sc=-dfs(b,2,-1e9,1e9);
        undo_move(b,m,st);
        if(sc>best){best=sc;bestm=m;}
    }
    return bestm;
}

// UCI loop
int main(){
    ios::sync_with_stdio(false);
    cin.tie(NULL);

    Board board;
    string line;
    while(getline(cin,line)){
        if(line=="uci"){
            cout<<"id name SmileyMate\nid author GPT\nuciok\n";
        }else if(line=="isready"){
            cout<<"readyok\n";
        }else if(line=="ucinewgame"){
            board.reset();
        }else if(line.rfind("position",0)==0){
            if(line.find("startpos")!=string::npos){
                board.reset();
                auto pos=line.find("moves");
                if(pos!=string::npos){
                    istringstream iss(line.substr(pos+6));
                    string m;
                    while(iss>>m){
                        State st; make_move(board,m,st);
                    }
                }
            }
        }else if(line.rfind("go",0)==0){
            string bm=search(board);
            cout<<"bestmove "<<bm<<"\n";
        }else if(line=="quit"){
            break;
        }
    }
    return 0;
}
