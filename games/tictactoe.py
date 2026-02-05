# -*- coding: utf-8 -*-
"""
井字棋游戏逻辑
"""
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Player(Enum):
    """玩家标识"""
    NONE = 0
    X = 1  # 先手
    O = 2  # 后手


@dataclass
class TicTacToeGame:
    """井字棋游戏状态"""
    player_x: str  # 先手玩家 ID
    player_o: Optional[str] = None  # 后手玩家 ID
    board: List[Player] = field(default_factory=lambda: [Player.NONE] * 9)
    current_turn: Player = Player.X
    winner: Optional[Player] = None
    is_finished: bool = False

    # 胜利条件：所有可能的三连线
    WIN_PATTERNS = [
        [0, 1, 2],  # 第一行
        [3, 4, 5],  # 第二行
        [6, 7, 8],  # 第三行
        [0, 3, 6],  # 第一列
        [1, 4, 7],  # 第二列
        [2, 5, 8],  # 第三列
        [0, 4, 8],  # 对角线
        [2, 4, 6],  # 反对角线
    ]

    def join(self, player_id: str) -> bool:
        """
        玩家加入游戏（作为后手 O）

        Args:
            player_id: 玩家 ID

        Returns:
            是否加入成功
        """
        if self.player_o is not None:
            return False
        if player_id == self.player_x:
            return False
        self.player_o = player_id
        return True

    def make_move(self, player_id: str, position: int) -> Tuple[bool, str]:
        """
        落子

        Args:
            player_id: 玩家 ID
            position: 位置 (1-9)

        Returns:
            (是否成功, 消息)
        """
        if self.is_finished:
            return False, "游戏已结束"

        if self.player_o is None:
            return False, "等待对手加入"

        # 检查是否轮到该玩家
        if self.current_turn == Player.X and player_id != self.player_x:
            return False, "现在是 X 方回合"
        if self.current_turn == Player.O and player_id != self.player_o:
            return False, "现在是 O 方回合"

        # 检查位置有效性
        if position < 1 or position > 9:
            return False, "位置应在 1-9 之间"

        idx = position - 1
        if self.board[idx] != Player.NONE:
            return False, "该位置已被占用"

        # 落子
        self.board[idx] = self.current_turn

        # 检查胜负
        if self._check_win(self.current_turn):
            self.winner = self.current_turn
            self.is_finished = True
            return True, "获胜"

        # 检查平局
        if all(cell != Player.NONE for cell in self.board):
            self.is_finished = True
            return True, "平局"

        # 切换回合
        self.current_turn = Player.O if self.current_turn == Player.X else Player.X
        return True, "落子成功"

    def _check_win(self, player: Player) -> bool:
        """检查是否获胜"""
        for pattern in self.WIN_PATTERNS:
            if all(self.board[i] == player for i in pattern):
                return True
        return False

    def surrender(self, player_id: str) -> Tuple[bool, str]:
        """
        认输

        Args:
            player_id: 认输的玩家 ID

        Returns:
            (是否成功, 消息)
        """
        if self.is_finished:
            return False, "游戏已结束"

        if player_id == self.player_x:
            self.winner = Player.O
            self.is_finished = True
            return True, "X 方认输"
        elif player_id == self.player_o:
            self.winner = Player.X
            self.is_finished = True
            return True, "O 方认输"
        else:
            return False, "你不是游戏参与者"

    def get_player_symbol(self, player_id: str) -> Optional[str]:
        """获取玩家的符号"""
        if player_id == self.player_x:
            return "X"
        elif player_id == self.player_o:
            return "O"
        return None

    def render_board(self) -> str:
        """渲染棋盘为文本"""
        symbols = {
            Player.NONE: "·",
            Player.X: "X",
            Player.O: "O",
        }

        lines = ["┌───┬───┬───┐"]
        for row in range(3):
            cells = []
            for col in range(3):
                idx = row * 3 + col
                cell = self.board[idx]
                if cell == Player.NONE:
                    # 显示位置数字
                    cells.append(f" {idx + 1} ")
                else:
                    cells.append(f" {symbols[cell]} ")
            lines.append("│" + "│".join(cells) + "│")
            if row < 2:
                lines.append("├───┼───┼───┤")
        lines.append("└───┴───┴───┘")

        return "\n".join(lines)

    def get_status_text(self, player_names: Dict[str, str] = None) -> str:
        """
        获取游戏状态文本

        Args:
            player_names: 玩家 ID 到昵称的映射
        """
        if player_names is None:
            player_names = {}

        x_name = player_names.get(self.player_x, self.player_x[:8])
        o_name = player_names.get(self.player_o, self.player_o[:8] if self.player_o else "等待加入")

        lines = [
            "🎮 井字棋",
            "━" * 14,
            "",
            self.render_board(),
            "",
        ]

        if self.is_finished:
            if self.winner == Player.X:
                lines.append(f"🏆 X 方 ({x_name}) 获胜！")
            elif self.winner == Player.O:
                lines.append(f"🏆 O 方 ({o_name}) 获胜！")
            else:
                lines.append("🤝 平局！")
        else:
            if self.player_o is None:
                lines.append(f"⏳ 等待对手加入...")
                lines.append(f"发送 /加入井字棋 参与游戏")
            else:
                turn_name = x_name if self.current_turn == Player.X else o_name
                turn_symbol = "X" if self.current_turn == Player.X else "O"
                lines.append(f"👉 轮到 {turn_symbol} 方 ({turn_name})")
                lines.append(f"发送 /下棋 <1-9> 落子")

        lines.extend([
            "",
            "━" * 14,
            f"X: {x_name}  |  O: {o_name}",
        ])

        return "\n".join(lines)


class TicTacToeManager:
    """井字棋游戏管理器"""

    def __init__(self):
        # 群号 -> 游戏实例
        self._games: Dict[str, TicTacToeGame] = {}

    def get_game(self, group_id: str) -> Optional[TicTacToeGame]:
        """获取群内的游戏"""
        return self._games.get(group_id)

    def create_game(self, group_id: str, player_id: str) -> Tuple[bool, str, Optional[TicTacToeGame]]:
        """
        创建新游戏

        Args:
            group_id: 群号
            player_id: 发起者 ID

        Returns:
            (是否成功, 消息, 游戏实例)
        """
        existing = self._games.get(group_id)
        if existing and not existing.is_finished:
            return False, "当前群已有进行中的游戏", existing

        game = TicTacToeGame(player_x=player_id)
        self._games[group_id] = game
        return True, "游戏创建成功", game

    def join_game(self, group_id: str, player_id: str) -> Tuple[bool, str, Optional[TicTacToeGame]]:
        """
        加入游戏

        Args:
            group_id: 群号
            player_id: 加入者 ID

        Returns:
            (是否成功, 消息, 游戏实例)
        """
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        if game.is_finished:
            return False, "游戏已结束，请发起新游戏", None

        if game.player_o is not None:
            return False, "游戏已满员", game

        if not game.join(player_id):
            return False, "你已经在游戏中了", game

        return True, "加入成功，游戏开始！", game

    def make_move(self, group_id: str, player_id: str, position: int) -> Tuple[bool, str, Optional[TicTacToeGame]]:
        """
        落子

        Args:
            group_id: 群号
            player_id: 玩家 ID
            position: 位置 (1-9)

        Returns:
            (是否成功, 消息, 游戏实例)
        """
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        success, msg = game.make_move(player_id, position)
        return success, msg, game

    def surrender(self, group_id: str, player_id: str) -> Tuple[bool, str, Optional[TicTacToeGame]]:
        """
        认输

        Args:
            group_id: 群号
            player_id: 玩家 ID

        Returns:
            (是否成功, 消息, 游戏实例)
        """
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        success, msg = game.surrender(player_id)
        return success, msg, game

    def end_game(self, group_id: str) -> bool:
        """强制结束游戏"""
        if group_id in self._games:
            del self._games[group_id]
            return True
        return False
