#!/usr/bin/env python
# -*- coding:utf-8 -*

import curses
import random
import redis
from itertools import chain


class Action(object):
    """ 根据键盘输入获取action """

    UP = 'up'
    DOWN = 'down'
    LEFT = 'left'
    RIGHT = 'right'
    RESTART = 'restart'
    EXIT = 'exit'
    CONTINUE = 'continue'

    actions = [UP, DOWN, LEFT, RIGHT, RESTART, EXIT]
    letter_codes = [ord(ch) for ch in 'WSADRQwsadrq']
    key_values = [259, 258, 260, 261]
    letter_codes.extend(key_values)
    action_dict = dict(zip(letter_codes, actions*3))

    letter_codes1 = [ord(ch) for ch in 'YNyn']  # 是否继续游戏
    action_dict.update(dict(zip(letter_codes1, [CONTINUE, EXIT]*2)))

    def __init__(self, stdscr):
        self.stdscr = stdscr

    def get(self):
        """ 根据键盘输入获取action并返回 """
        char = "N"
        if char not in self.action_dict:
            char = self.stdscr.getch()

        return self.action_dict[char]


class Grid(object):
    """ 游戏大小设置以及移动、合并 """

    def __init__(self, size, score=None):
        self.size = size
        self.score = score
        self.cells = None
        self.reset()

    def reset(self):
        """ 初始化游戏并随机生成两个数字 """
        self.cells = [[0 for i in range(self.size)] for j in range(self.size)]
        self.add_random_item()
        self.add_random_item()

    def add_random_item(self):
        """ 在空白处随机添加2或者4 """
        empty_cells = [(i, j) for i in range(self.size) for j in range(self.size) if self.cells[i][j] == 0]
        (i, j) = random.choice(empty_cells)
        self.cells[i][j] = 4 if random.randrange(100) >= 90 else 2

    def transpose(self):
        """ 颠倒 """
        self.cells = [list(row) for row in zip(*self.cells)]

    def invert(self):
        """ 反转 """
        self.cells = [row[::-1] for row in self.cells]

    # @staticmethod
    def move_row_left(self, row):
        """ 左移、合并 """
        def tighten(row):
            new_row = [i for i in row if i != 0]
            new_row += [0 for i in range(len(row) - len(new_row))]
            return new_row

        def merge(row):
            # 合并相同元素
            pair = False
            new_row = []
            # score = 0
            for i in range(len(row)):
                if pair:
                    new_row.append(2 * row[i])
                    self.score.score += 2 * row[i]
                    pair = False
                else:
                    if i + 1 < len(row) and row[i] == row[i+1]:
                        pair = True
                        new_row.append(0)
                    else:
                        new_row.append(row[i])
            assert len(new_row) == len(row)
            return new_row
        return tighten(merge(tighten(row)))

    def move_left(self):
        self.cells = [self.move_row_left(row) for row in self.cells]

    def move_right(self):
        self.invert()
        self.move_left()
        self.invert()

    def move_up(self):
        self.transpose()
        self.move_left()
        self.transpose()

    def move_down(self):
        self.transpose()
        self.move_right()
        self.transpose()

    @staticmethod
    def row_can_move_left(row):
        """ 判断是否可以往左移动 """
        def change(i):
            if row[i] == 0 and row[i+1] != 0:
                return True
            if row[i] != 0 and row[i+1] == row[i]:
                return True
            return False
        return any(change(i) for i in range(len(row) - 1))

    def can_move_left(self):
        return any(self.row_can_move_left(row) for row in self.cells)

    def can_move_right(self):
        self.invert()
        can = self.can_move_left()
        self.invert()
        return can

    def can_move_up(self):
        self.transpose()
        can = self.can_move_left()
        self.transpose()
        return can

    def can_move_down(self):
        self.transpose()
        can = self.can_move_right()
        self.transpose()
        return can


class Screen(object):
    """ 输出屏幕显示与提示 """

    help_string1 = '(W)Up (S)Down (A)Left (D)Right'
    help_string2 = '      (R)Restart (Q)Exit'
    over_string = '            GAME OVER'
    win_string = '           YOU WIN!'
    win_string2 = '    ARE YOU CONTINUE?(y/n)'

    def __init__(self, screen=None, grid=None, score=None, best_score=0, over=False, win=False, win_score=0):
        self.screen = screen
        self.grid = grid
        self.score = score
        self.best_score = best_score
        self.over = over
        self.win = win
        self.win_score = win_score

    def cast(self, string):
        """ 输出屏幕 """
        self.screen.addstr(string + '\n')

    def set_color(self, num):
        """ 输出颜色配置 """
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_YELLOW)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.start_color()
        # curses.init_color(curses.COLOR_YELLOW, (num * 10 + 156) * 4, (num * 10 + 102) * 4, (num * 10 + 31) * 4)
        # curses.init_color(curses.COLOR_YELLOW, num * 4, num * 4, num * 4)
        # curses.init_color(curses.COLOR_GREEN, 156 * 4, 102 * 4, 31 * 4)

    def draw_row(self, row):
        """ 输出一行 """
        # self.cast(''.join('|{: ^5}'.format(num) if num > 0 else '|     ' for num in row) + '|')
        for num in row:
            self.screen.addstr("|")
            if num > 0:
                # curses.init_color(curses.COLOR_YELLOW, 0, num, num)
                self.set_color(num)
                self.screen.addstr("{: ^5}".format(num), curses.color_pair(1))
            else:
                self.screen.addstr("     ", curses.color_pair(2))
        self.screen.addstr("|" + "\n")

    def draw(self):
        """ 显示游戏界面 """
        self.screen.clear()
        self.cast("SCORE: {score}   BEST SCORE: {best_score}".format(score=self.score.score,
                                                                     best_score=self.best_score))
        self.cast("       WIN SCORE: {}".format(self.win_score))
        for row in self.grid.cells:
            self.cast('+-----' * self.grid.size + '+')
            self.draw_row(row)
        self.cast('+-----' * self.grid.size + '+')

        if self.win:
            self.cast(self.win_string)
            self.cast(self.win_string2)
        else:
            if self.over:
                self.cast(self.over_string)
            else:
                self.cast(self.help_string1)

        self.cast(self.help_string2)


class Score(object):

    def __init__(self):
        self.score = 0


class GameManager(object):
    """ 游戏管理器 """

    def __init__(self, size=4, win_value=32):
        self.size = size
        self.win_value = win_value
        self.reset()

    def reset(self):
        self.state = 'init'
        self.win = False
        self.over = False
        self.score = Score()
        self.height_score = self.best_score()
        self.grid = Grid(self.size, self.score)
        self.grid.reset()

    @property
    def screen(self):
        return Screen(screen=self.stdscr, grid=self.grid, score=self.score,
                      best_score=self.height_score, win=self.win, over=self.over, win_score=self.win_value)

    def move(self, direction):
        if self.can_move(direction):
            getattr(self.grid, 'move_' + direction)()
            self.grid.add_random_item()
            return True
        else:
            return False

    @property
    def is_win(self):
        self.win = max(chain(*self.grid.cells)) >= self.win_value
        return self.win

    @property
    def is_over(self):
        self.over = not any(self.can_move(move) for move in self.action.actions)
        return self.over

    def can_move(self, direction):
        return getattr(self.grid, 'can_move_' + direction)()

    def best_score(self):
        """ 从redis读取最高分 """
        db_r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        score = int(db_r.get("best_score"))
        if self.score.score > score:
            db_r.set("best_score", self.score.score)
            return self.score.score
        return score

    def state_init(self):
        self.win_value = 32
        self.reset()
        return 'game'

    def state_game(self):
        self.screen.draw()
        action = self.action.get()

        if action == Action.RESTART:
            return 'init'
        elif action == Action.EXIT:
            return 'exit'
        if self.move(action):
            if self.is_win:
                return 'win'
            if self.is_over:
                return 'over'
        return 'game'

    def _restart_or_exit(self):
        """ 是否继续游戏，提高win_value值 """
        self.best_score()
        self.screen.draw()
        action = self.action.get()
        if action == Action.CONTINUE:
            self.win_value *= 2
            return 'game'
        elif action == Action.RESTART:
            return 'init'
        else:
            return 'exit'
        # return 'init' if action == Action.RESTART else 'exit'

    def state_win(self):
        return self._restart_or_exit()

    def state_over(self):
        return self._restart_or_exit()

    def __call__(self, stdscr):
        curses.use_default_colors()
        self.stdscr = stdscr
        self.action = Action(stdscr)

        while self.state != 'exit':
            self.state = getattr(self, 'state_' + self.state)()


if __name__ == '__main__':
    # print(Action.letter_codes)
    curses.wrapper(GameManager())
