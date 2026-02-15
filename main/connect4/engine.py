"""
Connect 4 game engine: board state, valid moves, win check, and CPU move evaluation.
"""


class Connect4Board:
    ROWS = 6
    COLS = 7
    P1 = "red"
    P2 = "yellow"

    def __init__(self, content=None):
        if content is not None:
            self.content = [list(row) for row in content]
        else:
            self.content = [[None] * self.COLS for _ in range(self.ROWS)]

    def valid_moves(self):
        moves = []
        for col in range(self.COLS):
            if self.content[self.ROWS - 1][col] is None:
                for row in range(self.ROWS):
                    if self.content[row][col] is None:
                        moves.append([col, row])
                        break
        return moves

    def push(self, move, player):
        col, row = move
        self.content[row][col] = player

    def pop(self, move):
        col, row = move
        self.content[row][col] = None

    def win_check(self, player, length=4):
        for r in range(self.ROWS):
            for c in range(self.COLS):
                if self.content[r][c] != player:
                    continue
                for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
                    count = 1
                    for step in range(1, length):
                        nr, nc = r + dr * step, c + dc * step
                        if 0 <= nr < self.ROWS and 0 <= nc < self.COLS and self.content[nr][nc] == player:
                            count += 1
                        else:
                            break
                    if count >= length:
                        return True
        return False

    def is_full(self):
        return all(self.content[self.ROWS - 1][c] is not None for c in range(self.COLS))

    def score_position(self, player, points):
        opponent = self.P2 if player == self.P1 else self.P1
        score = 0
        row_mult = points.get("row_mult", [1.5, 1.4, 1.3, 1.2, 1.1, 1.0])
        col_score = points.get("col_score", [5, 6, 7, 8, 7, 6, 5])
        for r in range(self.ROWS):
            for c in range(self.COLS):
                if self.content[r][c] == player:
                    score += row_mult[r] * col_score[c]
        if self.win_check(opponent, 4):
            score += points.get("loss_score", -100000)
        if self.win_check(player, 4):
            score += points.get("win_score", 10000)
        return score


def default_scoring():
    return {
        "win_score": 10000,
        "loss_score": -100000,
        "row_mult": [1.5, 1.4, 1.3, 1.2, 1.1, 1.0],
        "col_score": [5, 6, 7, 8, 7, 6, 5],
    }


def best_move(board_content):
    """Given board state (list of rows, None/red/yellow), return [col, row] for CPU (yellow)."""
    board = Connect4Board(content=board_content)
    points = default_scoring()
    moves = board.valid_moves()
    if not moves:
        return None
    best = None
    best_score = -10 ** 9
    for move in moves:
        board.push(move, Connect4Board.P2)
        opponent_best = -10 ** 9
        for opp_move in board.valid_moves():
            board.push(opp_move, Connect4Board.P1)
            s = board.score_position(Connect4Board.P1, points)
            if s > opponent_best:
                opponent_best = s
            board.pop(opp_move)
        board.pop(move)
        if opponent_best > best_score:
            best_score = opponent_best
            best = move
    return best


class Connect4Engine:
    """Thin wrapper for API: accepts board list, returns move [col, row]."""

    @staticmethod
    def get_cpu_move(board_state):
        return best_move(board_state)
