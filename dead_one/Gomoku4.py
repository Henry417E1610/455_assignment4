#!/usr/bin/env python
#/usr/local/bin/python3
# Set the path to your python3 above

from gtp_connection import GtpConnection
from board_util import GoBoardUtil, EMPTY, BLACK, WHITE
from simple_board import SimpleGoBoard
from mcts import MCTStree

import sys
import signal
import random
import numpy as np

WIN = 4
BLOCK_WIN = 3
OPEN_FOUR = 2
BLOCK_OPEN_FOUR = 1

def undo(board,move):
    board.board[move]=EMPTY
    board.current_player=GoBoardUtil.opponent(board.current_player)

def play_move(board, move, color):
    board.play_move_gomoku(move, color)

def game_result(board):
    game_end, winner = board.check_game_end_gomoku()
    moves = board.get_empty_points()
    board_full = (len(moves) == 0)
    if game_end:
        #return 1 if winner == board.current_player else -1
        return winner
    if board_full:
        return 'draw'
    return None

class HeuristicPolicy:
    def optimal_move(self,board,color):
        moves = board.get_empty_points()
        result = list(map(lambda m: (m, self._score(board, color, m)), moves))
        return sorted(moveResults, key=lambda res: res[1], reverse=True)
    
    def _score(self,board,color,m):
        board.play_move(m, board.current_player)
        score = self.evaluate(board,color)
        board.undo_move(m)
        return score

    def calculate_score(self,counts, color):
        category = [0, 1, 2, 5, 15, 1000000]
        if color == BLACK:
            player, opponent, empty = counts
        else:
            opponent, player, empty = counts

        # Is blocked
        if player >= 1 and opponent >= 1:
            return 0
        return category[player]-category[opponent]


    def evaluate(self,board, color):
        score = 0
        lines = board.rows + board.cols + board.diags

        for line in lines:
            for i in range(len(line) - 4):
                counts = self.get_counts(board, line[i:i+5])
                score += calculate_score(counts, color)

        return score

    def get_counts(self,board, five_line):
        blacks = 0
        whites = 0
        empties = 0

        for p in five_line:
            stone = board.board[p]
            if stone == BLACK:
                blacks += 1
            elif stone == WHITE:
                whites += 1
            else:
                empties += 1

        return blacks, whites, empties

class RulePolicy:
    def optimal_move(self,board,color):
        result = []
        for move in board.get_empty_points():
            score = self.check_move(board,color,move)
            result.append((move,score))
        result.sort(reverse=True, key=lambda x: x[1])
        return result
    
    def check_move(self, board, color, move):
        board.play_move_gomoku(move, color)
        
        row = move // (board.size+1) -1
        col = move % (board.size+1) -1
        newPoint = row*board.size+col
        
        maxScore = 0
        line5=[]
        for i in range(board.size*board.size):
            points = board.rows+board.cols+board.diags
            line5.append(points)
        board.undo_move(move)
        spec_line5=line5[newPoint]
        for l in spec_line5:
            for p in l:
                cond,win_color = board.check_game_end_gomoku()
                if win_color==color:
                    return 4
                elif board.detect_blockwin(color)!=None:
                    maxScore=max(3, maxScore)

        line6=[]
        diag6=[]
        for d in self.diags:
            if len(d)>=6:
                diag6.append(d)
        for i in range(board.size*board.size):
            points = board.rows+board.cols+diag6
            line6.append(points)
        spec_line6=line6[newPoint]
        for l in spec_line6:
            head=board.board[l[0]]
            tail=board.board[l[-1]]
            for p in l:
                if board.detect_openfour(color)!=None and head==EMPTY and tail==EMPTY:
                    maxScore = max(OPEN_FOUR, maxScore)
                elif board.detect_blockopenfour(color)!=None and head==color and tail==color:
                    blocked=False
                    if head==None or tail==None:
                        opponent_optimal=optimal_move(board,GoBoardUtil.opponent(color))
                        if opponent_optimal[0][1] < OPEN_FOUR:
                            blocked=True
                    else:
                        blocked=True
                    if blocked:
                        maxScore = max(BLOCK_OPEN_FOUR, maxScore)
                        
        board.undo_move(move)
        return maxScore
    
class CombinedPolicy:
    def __init__(self):
        self.rule_policy = RulePolicy()
        self.h_policy = HeuristicPolicy()
        
    def optimal_move(self,board,color):
        rule = self.rule_policy.optimal_move(board,color)
        best_move = []
        score = 0
        for move in rule:
            if move[1] > score:
                score = move[1]
            if move[1] < score:
                break
            best_move.append(move)
            
        if len(best_move) > 0:
            return best_move
        
        return self.h_policy.optimal_move(board,color)

class GomokuSimulationPlayer(object):
    """
    For each move do `n_simualtions_per_move` playouts,
    then select the one with best win-rate.
    playout could be either random or rule_based (i.e., uses pre-defined patterns) 
    """
    def __init__(self, n_simualtions_per_move=10, playout_policy='random', board_size=7):
        assert(playout_policy in ['random', 'rule_based'])
        self.n_simualtions_per_move=n_simualtions_per_move
        self.board_size=board_size
        self.playout_policy=playout_policy

        #NOTE: pattern has preference, later pattern is ignored if an earlier pattern is found
        self.pattern_list=['Win', 'BlockWin', 'OpenFour', 'BlockOpenFour', 'Random']

        self.name="Gomoku3"
        self.version = 3.0
        self.best_move=None
        self.timelimit = 59
    
    def set_playout_policy(self, playout_policy='random'):
        assert(playout_policy in ['random', 'rule_based'])
        self.playout_policy=playout_policy

    def _random_moves(self, board, color_to_play):
        return GoBoardUtil.generate_legal_moves_gomoku(board)
    
    def policy_moves(self, board, color_to_play):
        if(self.playout_policy=='random'):
            return "Random", self._random_moves(board, color_to_play)
        else:
            assert(self.playout_policy=='rule_based')
            assert(isinstance(board, SimpleGoBoard))
            ret=board.get_pattern_moves()
            if ret is None:
                return "Random", self._random_moves(board, color_to_play)
            movetype_id, moves=ret
            return self.pattern_list[movetype_id], moves
    
    def _do_playout(self, board, color_to_play):
        res=game_result(board)
        simulation_moves=[]
        while(res is None):
            _ , candidate_moves = self.policy_moves(board, board.current_player)
            playout_move=random.choice(candidate_moves)
            play_move(board, playout_move, board.current_player)
            simulation_moves.append(playout_move)
            res=game_result(board)
        for m in simulation_moves[::-1]:
            undo(board, m)
        if res == color_to_play:
            return 1.0
        elif res == 'draw':
            return 0.0
        else:
            assert(res == GoBoardUtil.opponent(color_to_play))
            return -1.0

    def get_move(self, board, color_to_play):
        """
        The genmove function called by gtp_connection
        """
        signal.alarm(self.timelimit)
        moves=GoBoardUtil.generate_legal_moves_gomoku(board)
        toplay=board.current_player
        best_result, best_move=-1.1, None
        best_move=moves[0]
        wins = np.zeros(len(moves))
        visits = np.zeros(len(moves))
        while True:
            for i, move in enumerate(moves):
                play_move(board, move, toplay)
                res=game_result(board)
                if res == toplay:
                    undo(board, move)
                    #This move is a immediate win
                    self.best_move=move
                    return move
                ret=self._do_playout(board, toplay)
                wins[i] += ret
                visits[i] += 1
                win_rate = wins[i] / visits[i]
                if win_rate > best_result:
                    best_result=win_rate
                    best_move=move
                    self.best_move=best_move
                undo(board, move)
                
                try:
                    mtree=MCTStree(board, color, CombinedPolicy())
                except TimeoutException:
                    return mtree.optimal_move()
                except Exception:
                    return mtree.optimal_move()             
        
        signal.alarm(0)
        assert(best_move is not None)
        return best_move

def run():
    """
    start the gtp connection and wait for commands.
    """
    board = SimpleGoBoard(7)
    con = GtpConnection(GomokuSimulationPlayer(), board)
    con.start_connection()

if __name__=='__main__':
    run()
