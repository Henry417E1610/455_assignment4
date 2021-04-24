from gtp_connection import format_point, point_to_coord
import random
import numpy as np

n=0

C = 2
NUM_SIMS = 50

def find(predict, array):
    for e in array:
        if predict(e):
            return e
    return None

class Node:
    def __init__(self, parent, move, color, boardsize):
        global n
        self.id = n
        n +=1
        
        self.parent=parent
        self.children=[]
        self.move = move
        self.color = color
        self.boardsize = boardsize
        self.expand = False
        self.winner = None
        
        if parent is None:
            self.move_list = []
        else:
            self.move_list = parent.move_list.copy()
            self.move_list.append(move)            
            
    def add_child(self, child):
        self.children.append(child)
            
    def add_winner(self,winner):
        self.winner = winner
        self.expand = True
        
    def __eq__(self, other):
            return other.id == self.id
        
class MCTStree:
    def __init__(self, board, color, policy):
            self.board = board
            opp_color = GoBoardUtil.opponent(color)
            self.root = MctsNode(None, None, opp_color, board.size)
            self.color = color
            self.policy = policy    
            
    def select(self):
        cur = self.root
        while True:
            if cur.expand and cur==self.root:
                selection=cur.children
            else:
                selection=[cur]+cur.children
        reselect=list(filter(lambda n: n.winner == EMPTY, selection))
        
        if len(reselect)==0:
            reselect=selection
            
    def expansion(self,node):
        copy=self.board.copy()
        for move in node.move_list:
            board_copy.play_move(move, copy.current_player)
            
        if node.expand:
            return node,copy
        
        expanded_move= set(map(lambda n: n.move, node.children))
        available_moves = len(copy.get_empty_points())
        optimal=self.policy.optimal_move(copy,copy.current_player)
        optimal=list(map(lambda x: x[0],optimal))
        next_move=find(lambda el: el not in expanded_move,optimal)
        
        opp_color = GoBoardUtil.opponent(node.color)
        next_node = Node(node, next_move, opp_color, self.board.size)
        node.add_child(next_node)
        
        if len(node.children) == len(optimal):
            node.expand=True
        if available_moves == 1:
            next_node.expand=True
            
        return next_node, copy

def mcts_step(mtree):
    selected=mtree.select()
    new_node,copy = tree.expand(selected)
    
