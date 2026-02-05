# -*- coding: utf-8 -*-
"""
军棋翻棋游戏逻辑
"""
import random
from typing import Optional, Dict, List, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class PieceType(Enum):
    """棋子类型"""
    EMPTY = 0
    FLAG = 1        # 军旗 - 不能移动，被吃则输
    MINE = 2        # 地雷 - 不能移动，除工兵外碰到都死
    BOMB = 3        # 炸弹 - 同归于尽
    COMMANDER = 4   # 司令 (最大)
    GENERAL = 5     # 军长
    DIVISION = 6    # 师长
    BRIGADE = 7     # 旅长
    REGIMENT = 8    # 团长
    BATTALION = 9   # 营长
    COMPANY = 10    # 连长
    PLATOON = 11    # 排长
    ENGINEER = 12   # 工兵 (最小，但能挖雷)


class Side(Enum):
    """阵营"""
    NONE = 0
    RED = 1
    BLUE = 2


# 棋子名称
PIECE_NAMES = {
    PieceType.FLAG: "军旗",
    PieceType.MINE: "地雷",
    PieceType.BOMB: "炸弹",
    PieceType.COMMANDER: "司令",
    PieceType.GENERAL: "军长",
    PieceType.DIVISION: "师长",
    PieceType.BRIGADE: "旅长",
    PieceType.REGIMENT: "团长",
    PieceType.BATTALION: "营长",
    PieceType.COMPANY: "连长",
    PieceType.PLATOON: "排长",
    PieceType.ENGINEER: "工兵",
}

# 棋子等级 (用于比较大小，越大越厉害)
PIECE_RANK = {
    PieceType.FLAG: 0,
    PieceType.MINE: 0,  # 特殊处理
    PieceType.BOMB: 0,  # 特殊处理
    PieceType.ENGINEER: 1,
    PieceType.PLATOON: 2,
    PieceType.COMPANY: 3,
    PieceType.BATTALION: 4,
    PieceType.REGIMENT: 5,
    PieceType.BRIGADE: 6,
    PieceType.DIVISION: 7,
    PieceType.GENERAL: 8,
    PieceType.COMMANDER: 9,
}

# 每方棋子配置 (25个)
PIECE_COUNT = {
    PieceType.FLAG: 1,
    PieceType.MINE: 3,
    PieceType.BOMB: 2,
    PieceType.COMMANDER: 1,
    PieceType.GENERAL: 1,
    PieceType.DIVISION: 2,
    PieceType.BRIGADE: 2,
    PieceType.REGIMENT: 2,
    PieceType.BATTALION: 2,
    PieceType.COMPANY: 3,
    PieceType.PLATOON: 3,
    PieceType.ENGINEER: 3,
}


@dataclass
class Piece:
    """棋子"""
    piece_type: PieceType
    side: Side
    revealed: bool = False  # 是否已翻开

    def get_name(self) -> str:
        return PIECE_NAMES.get(self.piece_type, "?")

    def get_rank(self) -> int:
        return PIECE_RANK.get(self.piece_type, 0)


@dataclass
class JunqiGame:
    """军棋翻棋游戏状态"""
    player_a: str  # 先手玩家 ID
    player_b: Optional[str] = None  # 后手玩家 ID
    player_a_side: Optional[Side] = None  # 玩家A的阵营（翻第一张牌决定）
    board: List[Optional[Piece]] = field(default_factory=list)  # 6x10 = 60 格棋盘
    current_turn: int = 1  # 1=玩家A先手, 2=玩家B
    move_count: int = 0
    last_action: Optional[str] = None  # 最后操作描述
    last_pos: Optional[int] = None  # 最后操作位置
    is_finished: bool = False
    winner: Optional[str] = None  # 胜利玩家 ID
    red_flag_captured: bool = False
    blue_flag_captured: bool = False

    # 棋盘尺寸
    ROWS: int = 10
    COLS: int = 6

    def __post_init__(self):
        """初始化棋盘"""
        if not self.board:
            self._init_board()

    def _init_board(self):
        """初始化棋盘，随机放置棋子（背面朝上）"""
        # 生成所有棋子
        pieces = []
        for piece_type, count in PIECE_COUNT.items():
            for _ in range(count):
                pieces.append(Piece(piece_type, Side.RED, revealed=False))
                pieces.append(Piece(piece_type, Side.BLUE, revealed=False))

        # 随机打乱
        random.shuffle(pieces)

        # 放置到棋盘 (60格，放50个棋子，留10个空位)
        total_cells = self.ROWS * self.COLS
        self.board = [None] * total_cells

        # 随机选择50个位置放棋子
        positions = list(range(total_cells))
        random.shuffle(positions)
        for i, piece in enumerate(pieces):
            self.board[positions[i]] = piece

    def _pos_to_xy(self, pos: int) -> Tuple[int, int]:
        """位置索引转坐标 (col, row)"""
        return pos % self.COLS, pos // self.COLS

    def _xy_to_pos(self, x: int, y: int) -> int:
        """坐标转位置索引"""
        return y * self.COLS + x

    def _get_neighbors(self, pos: int) -> List[int]:
        """获取相邻位置（上下左右）"""
        x, y = self._pos_to_xy(pos)
        neighbors = []
        if x > 0:
            neighbors.append(self._xy_to_pos(x - 1, y))
        if x < self.COLS - 1:
            neighbors.append(self._xy_to_pos(x + 1, y))
        if y > 0:
            neighbors.append(self._xy_to_pos(x, y - 1))
        if y < self.ROWS - 1:
            neighbors.append(self._xy_to_pos(x, y + 1))
        return neighbors

    def join(self, player_id: str) -> bool:
        """加入游戏"""
        if self.player_b is not None:
            return False
        if player_id == self.player_a:
            return False
        self.player_b = player_id
        return True

    def get_current_player(self) -> str:
        """获取当前行动玩家"""
        return self.player_a if self.current_turn == 1 else self.player_b

    def get_player_side(self, player_id: str) -> Optional[Side]:
        """获取玩家阵营"""
        if self.player_a_side is None:
            return None
        if player_id == self.player_a:
            return self.player_a_side
        elif player_id == self.player_b:
            return Side.BLUE if self.player_a_side == Side.RED else Side.RED
        return None

    def flip(self, player_id: str, pos: int) -> Tuple[bool, str]:
        """
        翻棋

        Args:
            player_id: 玩家 ID
            pos: 位置

        Returns:
            (是否成功, 消息)
        """
        if self.is_finished:
            return False, "游戏已结束"

        if self.player_b is None:
            return False, "等待对手加入"

        # 检查是否轮到该玩家
        if player_id != self.get_current_player():
            return False, "还没轮到你"

        # 检查位置有效性
        if not (0 <= pos < self.ROWS * self.COLS):
            return False, "位置无效"

        piece = self.board[pos]
        if piece is None:
            return False, "该位置没有棋子"

        if piece.revealed:
            return False, "该棋子已经翻开了"

        # 翻开棋子
        piece.revealed = True

        # 如果是第一次翻棋，决定阵营
        if self.player_a_side is None:
            self.player_a_side = piece.side
            side_name = "红方" if piece.side == Side.RED else "蓝方"
            self.last_action = f"翻开 {piece.get_name()}，成为{side_name}"
        else:
            self.last_action = f"翻开 {piece.get_name()}"

        self.last_pos = pos
        self.move_count += 1
        self._switch_turn()

        return True, self.last_action

    def move(self, player_id: str, from_pos: int, to_pos: int) -> Tuple[bool, str]:
        """
        移动棋子或吃子

        Args:
            player_id: 玩家 ID
            from_pos: 起始位置
            to_pos: 目标位置

        Returns:
            (是否成功, 消息)
        """
        if self.is_finished:
            return False, "游戏已结束"

        if self.player_b is None:
            return False, "等待对手加入"

        if player_id != self.get_current_player():
            return False, "还没轮到你"

        if self.player_a_side is None:
            return False, "请先翻棋确定阵营"

        # 检查位置有效性
        if not (0 <= from_pos < self.ROWS * self.COLS):
            return False, "起始位置无效"
        if not (0 <= to_pos < self.ROWS * self.COLS):
            return False, "目标位置无效"

        piece = self.board[from_pos]
        if piece is None:
            return False, "起始位置没有棋子"

        if not piece.revealed:
            return False, "不能移动未翻开的棋子"

        # 检查是否是自己的棋子
        player_side = self.get_player_side(player_id)
        if piece.side != player_side:
            return False, "这不是你的棋子"

        # 检查是否可移动（地雷和军旗不能移动）
        if piece.piece_type in [PieceType.MINE, PieceType.FLAG]:
            return False, f"{piece.get_name()}不能移动"

        # 检查是否相邻
        if to_pos not in self._get_neighbors(from_pos):
            return False, "只能移动到相邻位置"

        target = self.board[to_pos]

        # 目标是空位 - 直接移动
        if target is None:
            self.board[to_pos] = piece
            self.board[from_pos] = None
            self.last_action = f"{piece.get_name()} 移动"
            self.last_pos = to_pos
            self.move_count += 1
            self._switch_turn()
            return True, self.last_action

        # 目标是未翻开的棋子 - 不能移动到那里
        if not target.revealed:
            return False, "不能移动到未翻开的棋子上"

        # 目标是己方棋子 - 不能吃
        if target.side == player_side:
            return False, "不能吃自己的棋子"

        # 吃子逻辑
        result = self._battle(piece, target)
        target_name = target.get_name()

        if result == "win":
            # 攻方胜
            self.board[to_pos] = piece
            self.board[from_pos] = None
            self.last_action = f"{piece.get_name()} 吃掉 {target_name}"
        elif result == "lose":
            # 攻方败
            self.board[from_pos] = None
            self.last_action = f"{piece.get_name()} 被 {target_name} 吃掉"
        else:
            # 同归于尽
            self.board[from_pos] = None
            self.board[to_pos] = None
            self.last_action = f"{piece.get_name()} 与 {target_name} 同归于尽"

        # 检查是否吃掉军旗
        if target.piece_type == PieceType.FLAG:
            if target.side == Side.RED:
                self.red_flag_captured = True
            else:
                self.blue_flag_captured = True
            self._check_game_end()

        self.last_pos = to_pos
        self.move_count += 1
        self._switch_turn()

        return True, self.last_action

    def _battle(self, attacker: Piece, defender: Piece) -> str:
        """
        战斗判定

        Returns:
            "win" - 攻方胜
            "lose" - 攻方败
            "draw" - 同归于尽
        """
        # 炸弹：同归于尽
        if attacker.piece_type == PieceType.BOMB or defender.piece_type == PieceType.BOMB:
            return "draw"

        # 地雷：只有工兵能挖
        if defender.piece_type == PieceType.MINE:
            if attacker.piece_type == PieceType.ENGINEER:
                return "win"
            else:
                return "draw"  # 碰地雷同归于尽

        # 军旗：任何棋子都能吃（实际游戏中需要先挖雷）
        if defender.piece_type == PieceType.FLAG:
            return "win"

        # 普通比较
        atk_rank = attacker.get_rank()
        def_rank = defender.get_rank()

        if atk_rank > def_rank:
            return "win"
        elif atk_rank < def_rank:
            return "lose"
        else:
            return "draw"

    def _switch_turn(self):
        """切换回合"""
        self.current_turn = 2 if self.current_turn == 1 else 1

    def _check_game_end(self):
        """检查游戏是否结束"""
        if self.red_flag_captured:
            # 红旗被吃，蓝方胜
            self.is_finished = True
            if self.player_a_side == Side.BLUE:
                self.winner = self.player_a
            else:
                self.winner = self.player_b
        elif self.blue_flag_captured:
            # 蓝旗被吃，红方胜
            self.is_finished = True
            if self.player_a_side == Side.RED:
                self.winner = self.player_a
            else:
                self.winner = self.player_b

    def surrender(self, player_id: str) -> Tuple[bool, str]:
        """认输"""
        if self.is_finished:
            return False, "游戏已结束"

        if player_id == self.player_a:
            self.winner = self.player_b
            self.is_finished = True
            return True, "玩家A认输"
        elif player_id == self.player_b:
            self.winner = self.player_a
            self.is_finished = True
            return True, "玩家B认输"
        else:
            return False, "你不是游戏参与者"

    def parse_coordinate(self, coord_str: str) -> Optional[int]:
        """
        解析坐标字符串
        支持格式：A1, a1, 1,1, 1-1
        """
        coord_str = coord_str.strip().upper()

        # 尝试解析字母+数字格式 (A1)
        if len(coord_str) >= 2:
            col = coord_str[0]
            row_str = coord_str[1:]

            if col in "ABCDEF":
                try:
                    row = int(row_str)
                    if 1 <= row <= self.ROWS:
                        x = "ABCDEF".index(col)
                        y = row - 1
                        return self._xy_to_pos(x, y)
                except ValueError:
                    pass

        # 尝试解析数字,数字格式 (1,1)
        for sep in [',', '-', ' ']:
            if sep in coord_str:
                parts = coord_str.split(sep)
                if len(parts) == 2:
                    try:
                        x = int(parts[0]) - 1
                        y = int(parts[1]) - 1
                        if 0 <= x < self.COLS and 0 <= y < self.ROWS:
                            return self._xy_to_pos(x, y)
                    except ValueError:
                        pass

        return None

    def get_coordinate_label(self, pos: int) -> str:
        """获取位置的坐标标签"""
        x, y = self._pos_to_xy(pos)
        return f"{'ABCDEF'[x]}{y + 1}"

    def get_board_for_render(self, viewer_id: Optional[str] = None) -> List[dict]:
        """
        获取用于渲染的棋盘数据

        Args:
            viewer_id: 查看者ID（决定哪些棋子可见）

        Returns:
            棋盘数据列表
        """
        viewer_side = self.get_player_side(viewer_id) if viewer_id else None
        result = []

        for pos in range(self.ROWS * self.COLS):
            piece = self.board[pos]
            if piece is None:
                result.append({"type": "empty"})
            elif piece.revealed:
                result.append({
                    "type": "revealed",
                    "piece": piece.piece_type.name,
                    "side": piece.side.name,
                    "name": piece.get_name()
                })
            else:
                # 未翻开的棋子
                result.append({"type": "hidden"})

        return result


class JunqiManager:
    """军棋游戏管理器"""

    def __init__(self):
        self._games: Dict[str, JunqiGame] = {}

    def get_game(self, group_id: str) -> Optional[JunqiGame]:
        """获取群内的游戏"""
        return self._games.get(group_id)

    def create_game(
        self, group_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[JunqiGame]]:
        """创建新游戏"""
        existing = self._games.get(group_id)
        if existing and not existing.is_finished:
            return False, "当前群已有进行中的游戏", existing

        game = JunqiGame(player_a=player_id)
        self._games[group_id] = game
        return True, "游戏创建成功", game

    def join_game(
        self, group_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[JunqiGame]]:
        """加入游戏"""
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        if game.is_finished:
            return False, "游戏已结束，请发起新游戏", None

        if game.player_b is not None:
            return False, "游戏已满员", game

        if not game.join(player_id):
            return False, "你已经在游戏中了", game

        return True, "加入成功，游戏开始！先手翻棋决定阵营", game

    def flip(
        self, group_id: str, player_id: str, coord_str: str
    ) -> Tuple[bool, str, Optional[JunqiGame]]:
        """翻棋"""
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        pos = game.parse_coordinate(coord_str)
        if pos is None:
            return False, "坐标格式错误，请使用如 A1 或 1,1 的格式", None

        success, msg = game.flip(player_id, pos)
        return success, msg, game

    def move(
        self, group_id: str, player_id: str, move_str: str
    ) -> Tuple[bool, str, Optional[JunqiGame]]:
        """移动/吃子"""
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        # 解析移动字符串 (A1-A2 或 A1A2)
        move_str = move_str.strip().upper()

        from_pos = None
        to_pos = None

        # 尝试解析 A1-A2 格式
        if '-' in move_str:
            parts = move_str.split('-')
            if len(parts) == 2:
                from_pos = game.parse_coordinate(parts[0])
                to_pos = game.parse_coordinate(parts[1])
        elif '>' in move_str:
            parts = move_str.split('>')
            if len(parts) == 2:
                from_pos = game.parse_coordinate(parts[0])
                to_pos = game.parse_coordinate(parts[1])
        else:
            # 尝试解析无分隔符格式 (A1A2, A10B1 etc.)
            # 寻找第二个字母的位置
            split_idx = -1
            for i in range(1, len(move_str)):
                if move_str[i].isalpha():
                    split_idx = i
                    break
            
            if split_idx != -1:
                from_pos = game.parse_coordinate(move_str[:split_idx])
                to_pos = game.parse_coordinate(move_str[split_idx:])

        if from_pos is None or to_pos is None:
            return False, "移动格式错误，请使用如 A1-A2 的格式", None

        success, msg = game.move(player_id, from_pos, to_pos)
        return success, msg, game

    def surrender(
        self, group_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[JunqiGame]]:
        """认输"""
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
