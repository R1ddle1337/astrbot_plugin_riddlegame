# -*- coding: utf-8 -*-
"""
中国象棋游戏逻辑
"""
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Piece(Enum):
    """棋子类型"""
    EMPTY = 0
    # 红方棋子 (1-7)
    R_KING = 1      # 帅
    R_ADVISOR = 2   # 仕
    R_ELEPHANT = 3  # 相
    R_HORSE = 4     # 马
    R_CHARIOT = 5   # 车
    R_CANNON = 6    # 炮
    R_SOLDIER = 7   # 兵
    # 黑方棋子 (8-14)
    B_KING = 8      # 将
    B_ADVISOR = 9   # 士
    B_ELEPHANT = 10 # 象
    B_HORSE = 11    # 馬
    B_CHARIOT = 12  # 車
    B_CANNON = 13   # 砲
    B_SOLDIER = 14  # 卒


class Side(Enum):
    """阵营"""
    RED = 1   # 红方先手
    BLACK = 2 # 黑方后手


# 棋子显示名称
PIECE_NAMES = {
    Piece.EMPTY: "　",
    Piece.R_KING: "帅", Piece.R_ADVISOR: "仕", Piece.R_ELEPHANT: "相",
    Piece.R_HORSE: "马", Piece.R_CHARIOT: "车", Piece.R_CANNON: "炮", Piece.R_SOLDIER: "兵",
    Piece.B_KING: "将", Piece.B_ADVISOR: "士", Piece.B_ELEPHANT: "象",
    Piece.B_HORSE: "馬", Piece.B_CHARIOT: "車", Piece.B_CANNON: "砲", Piece.B_SOLDIER: "卒",
}

# 棋子渲染代码
PIECE_CODES = {
    Piece.EMPTY: "",
    Piece.R_KING: "RK", Piece.R_ADVISOR: "RA", Piece.R_ELEPHANT: "RE",
    Piece.R_HORSE: "RH", Piece.R_CHARIOT: "RC", Piece.R_CANNON: "RN", Piece.R_SOLDIER: "RS",
    Piece.B_KING: "BK", Piece.B_ADVISOR: "BA", Piece.B_ELEPHANT: "BE",
    Piece.B_HORSE: "BH", Piece.B_CHARIOT: "BC", Piece.B_CANNON: "BN", Piece.B_SOLDIER: "BS",
}

# 中式记谱法：棋子名称映射
CHINESE_PIECE_NAMES = {
    # 红方
    "帅": [Piece.R_KING], "仕": [Piece.R_ADVISOR], "相": [Piece.R_ELEPHANT],
    "马": [Piece.R_HORSE], "车": [Piece.R_CHARIOT], "炮": [Piece.R_CANNON], "兵": [Piece.R_SOLDIER],
    # 黑方
    "将": [Piece.B_KING], "士": [Piece.B_ADVISOR], "象": [Piece.B_ELEPHANT],
    "馬": [Piece.B_HORSE], "車": [Piece.B_CHARIOT], "砲": [Piece.B_CANNON], "卒": [Piece.B_SOLDIER],
    # 通用名称（根据当前回合判断）
    "帥": [Piece.R_KING], "仕": [Piece.R_ADVISOR, Piece.B_ADVISOR],
    "俥": [Piece.R_CHARIOT], "傌": [Piece.R_HORSE], "包": [Piece.R_CANNON],
}

# 中式记谱法：数字映射（一到九）
CHINESE_NUMBERS = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6, "7": 7, "8": 8, "9": 9,
    "０": 0, "１": 1, "２": 2, "３": 3, "４": 4,
    "５": 5, "６": 6, "７": 7, "８": 8, "９": 9,
}

# 中式记谱法：动作
CHINESE_ACTIONS = {
    "进": "forward", "進": "forward",
    "退": "backward", "后": "backward",
    "平": "horizontal",
}

# 中式记谱法：前后标识
CHINESE_POSITION = {
    "前": "front", "後": "front",
    "后": "back", "後": "back",
    "中": "middle",
}

# 列标签
COLUMN_LABELS = "ABCDEFGHI"

# 初始棋盘布局 (row 0 是红方底线，row 9 是黑方底线)
INITIAL_BOARD = [
    # Row 0 (红方底线): 车马相仕帅仕相马车
    Piece.R_CHARIOT, Piece.R_HORSE, Piece.R_ELEPHANT, Piece.R_ADVISOR, Piece.R_KING,
    Piece.R_ADVISOR, Piece.R_ELEPHANT, Piece.R_HORSE, Piece.R_CHARIOT,
    # Row 1: 空
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    # Row 2: 炮
    Piece.EMPTY, Piece.R_CANNON, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    Piece.EMPTY, Piece.EMPTY, Piece.R_CANNON, Piece.EMPTY,
    # Row 3: 兵
    Piece.R_SOLDIER, Piece.EMPTY, Piece.R_SOLDIER, Piece.EMPTY, Piece.R_SOLDIER,
    Piece.EMPTY, Piece.R_SOLDIER, Piece.EMPTY, Piece.R_SOLDIER,
    # Row 4: 空 (楚河)
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    # Row 5: 空 (汉界)
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    # Row 6: 卒
    Piece.B_SOLDIER, Piece.EMPTY, Piece.B_SOLDIER, Piece.EMPTY, Piece.B_SOLDIER,
    Piece.EMPTY, Piece.B_SOLDIER, Piece.EMPTY, Piece.B_SOLDIER,
    # Row 7: 砲
    Piece.EMPTY, Piece.B_CANNON, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    Piece.EMPTY, Piece.EMPTY, Piece.B_CANNON, Piece.EMPTY,
    # Row 8: 空
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    Piece.EMPTY, Piece.EMPTY, Piece.EMPTY, Piece.EMPTY,
    # Row 9 (黑方底线): 車馬象士将士象馬車
    Piece.B_CHARIOT, Piece.B_HORSE, Piece.B_ELEPHANT, Piece.B_ADVISOR, Piece.B_KING,
    Piece.B_ADVISOR, Piece.B_ELEPHANT, Piece.B_HORSE, Piece.B_CHARIOT,
]


def get_piece_side(piece: Piece) -> Optional[Side]:
    """获取棋子所属阵营"""
    if piece == Piece.EMPTY:
        return None
    return Side.RED if piece.value <= 7 else Side.BLACK


@dataclass
class XiangqiGame:
    """中国象棋游戏状态"""
    player_red: str  # 红方玩家 ID
    player_black: Optional[str] = None  # 黑方玩家 ID
    board: List[Piece] = field(default_factory=list)
    current_turn: Side = Side.RED
    move_count: int = 0
    last_move: Optional[Tuple[int, int]] = None  # (from_pos, to_pos)
    is_finished: bool = False
    winner: Optional[Side] = None
    in_check: bool = False  # 当前方是否被将军

    def __post_init__(self):
        """初始化棋盘"""
        if not self.board:
            self.board = INITIAL_BOARD.copy()

    def _pos_to_rc(self, pos: int) -> Tuple[int, int]:
        """位置索引转行列 (row, col)"""
        return pos // 9, pos % 9

    def _rc_to_pos(self, row: int, col: int) -> int:
        """行列转位置索引"""
        return row * 9 + col

    def _is_valid_pos(self, row: int, col: int) -> bool:
        """检查位置是否在棋盘内"""
        return 0 <= row < 10 and 0 <= col < 9

    def _get_opponent(self, side: Side) -> Side:
        """获取对方阵营"""
        return Side.BLACK if side == Side.RED else Side.RED

    def join(self, player_id: str) -> bool:
        """加入游戏（黑方）"""
        if self.player_black is not None:
            return False
        if player_id == self.player_red:
            return False
        self.player_black = player_id
        return True

    def parse_move(self, move_str: str) -> Optional[Tuple[int, int]]:
        """
        解析走法字符串
        支持格式：
        - E1-E2, e1-e2 (字母+数字)
        - 5,1-5,2 (数字,数字)
        - 炮二进四, 前车进三 (中式记谱法)
        返回 (from_pos, to_pos) 或 None
        """
        move_str = move_str.strip().replace(" ", "")

        # 首先尝试坐标格式 (E1-E2, 5,1-5,2, 或 H2E2)
        result = self._parse_coordinate_move(move_str)
        if result:
            return result

        # 尝试中式记谱法
        result = self._parse_chinese_move(move_str)
        if result:
            return result

        return None

    def _parse_coordinate_move(self, move_str: str) -> Optional[Tuple[int, int]]:
        """解析坐标格式走法 (E1-E2, 5,1-5,2, H2E2)"""
        move_str = move_str.upper()

        parts = []
        # 分割起点和终点
        if "-" in move_str:
            parts = move_str.split("-")
        elif ">" in move_str:
            parts = move_str.split(">")
        elif "," not in move_str:
            # 尝试无分隔符格式 (如 H2E2, A10B5)
            # 寻找第二个字母的位置
            split_idx = -1
            for i in range(1, len(move_str)):
                if move_str[i].isalpha():
                    split_idx = i
                    break
            
            if split_idx != -1:
                parts = [move_str[:split_idx], move_str[split_idx:]]
            else:
                return None
        else:
            return None

        if len(parts) != 2:
            return None

        from_coord = self._parse_coordinate(parts[0])
        to_coord = self._parse_coordinate(parts[1])

        if from_coord is None or to_coord is None:
            return None

        from_pos = self._rc_to_pos(from_coord[0], from_coord[1])
        to_pos = self._rc_to_pos(to_coord[0], to_coord[1])

        return (from_pos, to_pos)

    def _parse_coordinate(self, coord_str: str) -> Optional[Tuple[int, int]]:
        """
        解析单个坐标
        返回 (row, col) 或 None
        """
        coord_str = coord_str.strip().upper()

        # 尝试字母+数字格式 (A1-I10)
        if len(coord_str) >= 2 and coord_str[0] in COLUMN_LABELS:
            col = COLUMN_LABELS.index(coord_str[0])
            try:
                row = int(coord_str[1:]) - 1  # 转为 0-indexed
                if 0 <= row < 10 and 0 <= col < 9:
                    return (row, col)
            except ValueError:
                pass

        # 尝试数字,数字格式
        if "," in coord_str:
            parts = coord_str.split(",")
            if len(parts) == 2:
                try:
                    col = int(parts[0]) - 1  # 列 1-9 转为 0-8
                    row = int(parts[1]) - 1  # 行 1-10 转为 0-9
                    if 0 <= row < 10 and 0 <= col < 9:
                        return (row, col)
                except ValueError:
                    pass

        return None

    def _parse_chinese_move(self, move_str: str) -> Optional[Tuple[int, int]]:
        """
        解析中式记谱法
        格式：棋子 + 列号 + 动作 + 步数/列号
        例如：炮二进四, 车八平五, 前马进七
        """
        if len(move_str) < 4:
            return None

        # 检查是否有前/后/中标识
        position_marker = None
        start_idx = 0
        if move_str[0] in CHINESE_POSITION:
            position_marker = CHINESE_POSITION[move_str[0]]
            start_idx = 1

        # 解析棋子
        piece_char = move_str[start_idx]
        if piece_char not in CHINESE_PIECE_NAMES:
            return None

        possible_pieces = CHINESE_PIECE_NAMES[piece_char]

        # 根据当前回合过滤棋子
        side = self.current_turn
        valid_pieces = []
        for p in possible_pieces:
            if get_piece_side(p) == side:
                valid_pieces.append(p)

        if not valid_pieces:
            return None

        # 解析列号（棋子所在的列）
        col_char = move_str[start_idx + 1]
        if col_char not in CHINESE_NUMBERS:
            return None
        orig_col = CHINESE_NUMBERS[col_char]

        # 红方列号从右往左数（9到1对应0到8）
        # 黑方列号也从右往左数（1到9对应8到0）
        if side == Side.RED:
            from_col = 9 - orig_col  # 红方：一列=第8列(index 8), 九列=第0列(index 0)
        else:
            from_col = orig_col - 1  # 黑方：一列=第0列(index 0), 九列=第8列(index 8)

        # 解析动作
        action_char = move_str[start_idx + 2]
        if action_char not in CHINESE_ACTIONS:
            return None
        action = CHINESE_ACTIONS[action_char]

        # 解析步数/目标列
        target_char = move_str[start_idx + 3]
        if target_char not in CHINESE_NUMBERS:
            return None
        target_num = CHINESE_NUMBERS[target_char]

        # 找到棋子位置
        candidates = []
        for pos, piece in enumerate(self.board):
            if piece in valid_pieces:
                row, col = self._pos_to_rc(pos)
                if col == from_col:
                    candidates.append((pos, row, col))

        if not candidates:
            return None

        # 如果有多个同列的棋子，使用前/后标识筛选
        if len(candidates) > 1:
            # 按行排序
            if side == Side.RED:
                # 红方：前=行号大（靠近黑方），后=行号小（靠近己方）
                candidates.sort(key=lambda x: x[1], reverse=True)
            else:
                # 黑方：前=行号小（靠近红方），后=行号大（靠近己方）
                candidates.sort(key=lambda x: x[1])

            if position_marker == "front":
                candidates = [candidates[0]]
            elif position_marker == "back":
                candidates = [candidates[-1]]
            elif position_marker == "middle" and len(candidates) >= 3:
                candidates = [candidates[len(candidates) // 2]]
            else:
                # 没有标识但有多个棋子，无法确定
                return None

        if len(candidates) != 1:
            return None

        from_pos, from_row, from_col = candidates[0]

        # 计算目标位置
        piece = self.board[from_pos]

        if action == "horizontal":
            # 平移：target_num 是目标列
            if side == Side.RED:
                to_col = 9 - target_num
            else:
                to_col = target_num - 1
            to_row = from_row
        else:
            # 进/退
            steps = target_num

            # 判断棋子是直行还是斜行
            is_straight = piece in (
                Piece.R_CHARIOT, Piece.B_CHARIOT,  # 车
                Piece.R_CANNON, Piece.B_CANNON,    # 炮
                Piece.R_KING, Piece.B_KING,        # 将帅
                Piece.R_SOLDIER, Piece.B_SOLDIER,  # 兵卒
            )

            if is_straight:
                # 直行棋子：steps 是移动的格数
                if action == "forward":
                    if side == Side.RED:
                        to_row = from_row + steps
                    else:
                        to_row = from_row - steps
                else:  # backward
                    if side == Side.RED:
                        to_row = from_row - steps
                    else:
                        to_row = from_row + steps
                to_col = from_col
            else:
                # 斜行棋子（马、相、仕）：target_num 是目标列
                if side == Side.RED:
                    to_col = 9 - target_num
                else:
                    to_col = target_num - 1

                # 根据棋子类型和目标列计算目标行
                dc = abs(to_col - from_col)

                if piece in (Piece.R_HORSE, Piece.B_HORSE):
                    # 马：日字走法
                    if dc == 1:
                        dr = 2
                    elif dc == 2:
                        dr = 1
                    else:
                        return None
                elif piece in (Piece.R_ELEPHANT, Piece.B_ELEPHANT):
                    # 象/相：田字走法
                    if dc != 2:
                        return None
                    dr = 2
                elif piece in (Piece.R_ADVISOR, Piece.B_ADVISOR):
                    # 仕/士：斜走一步
                    if dc != 1:
                        return None
                    dr = 1
                else:
                    return None

                if action == "forward":
                    if side == Side.RED:
                        to_row = from_row + dr
                    else:
                        to_row = from_row - dr
                else:  # backward
                    if side == Side.RED:
                        to_row = from_row - dr
                    else:
                        to_row = from_row + dr

        # 验证目标位置
        if not self._is_valid_pos(to_row, to_col):
            return None

        to_pos = self._rc_to_pos(to_row, to_col)
        return (from_pos, to_pos)

    def _find_king(self, side: Side) -> Optional[int]:
        """找到指定方的将/帅位置"""
        king = Piece.R_KING if side == Side.RED else Piece.B_KING
        for i, piece in enumerate(self.board):
            if piece == king:
                return i
        return None

    def _is_in_palace(self, row: int, col: int, side: Side) -> bool:
        """检查位置是否在九宫内"""
        if col < 3 or col > 5:
            return False
        if side == Side.RED:
            return 0 <= row <= 2
        else:
            return 7 <= row <= 9

    def _is_across_river(self, row: int, side: Side) -> bool:
        """检查是否过河"""
        if side == Side.RED:
            return row >= 5
        else:
            return row <= 4

    def _get_pieces_between(self, from_pos: int, to_pos: int) -> int:
        """获取两点之间的棋子数（用于车炮的直线移动）"""
        from_row, from_col = self._pos_to_rc(from_pos)
        to_row, to_col = self._pos_to_rc(to_pos)

        count = 0

        if from_row == to_row:
            # 横向
            start_col = min(from_col, to_col) + 1
            end_col = max(from_col, to_col)
            for c in range(start_col, end_col):
                if self.board[self._rc_to_pos(from_row, c)] != Piece.EMPTY:
                    count += 1
        elif from_col == to_col:
            # 纵向
            start_row = min(from_row, to_row) + 1
            end_row = max(from_row, to_row)
            for r in range(start_row, end_row):
                if self.board[self._rc_to_pos(r, from_col)] != Piece.EMPTY:
                    count += 1

        return count

    def _is_valid_piece_move(self, from_pos: int, to_pos: int) -> bool:
        """检查棋子走法是否合法（不考虑将军）"""
        piece = self.board[from_pos]
        if piece == Piece.EMPTY:
            return False

        from_row, from_col = self._pos_to_rc(from_pos)
        to_row, to_col = self._pos_to_rc(to_pos)

        # 不能原地不动
        if from_pos == to_pos:
            return False

        # 不能吃自己的子
        target = self.board[to_pos]
        if target != Piece.EMPTY:
            if get_piece_side(piece) == get_piece_side(target):
                return False

        side = get_piece_side(piece)
        dr = to_row - from_row
        dc = to_col - from_col

        # 根据棋子类型验证
        if piece in (Piece.R_KING, Piece.B_KING):
            # 帅/将：九宫内一步直行
            if not self._is_in_palace(to_row, to_col, side):
                return False
            if abs(dr) + abs(dc) != 1:
                return False
            return True

        elif piece in (Piece.R_ADVISOR, Piece.B_ADVISOR):
            # 仕/士：九宫内斜走一步
            if not self._is_in_palace(to_row, to_col, side):
                return False
            if abs(dr) != 1 or abs(dc) != 1:
                return False
            return True

        elif piece in (Piece.R_ELEPHANT, Piece.B_ELEPHANT):
            # 相/象：田字斜走，不能过河，塞象眼
            if self._is_across_river(to_row, side):
                return False
            if abs(dr) != 2 or abs(dc) != 2:
                return False
            # 检查象眼
            eye_row = from_row + dr // 2
            eye_col = from_col + dc // 2
            if self.board[self._rc_to_pos(eye_row, eye_col)] != Piece.EMPTY:
                return False
            return True

        elif piece in (Piece.R_HORSE, Piece.B_HORSE):
            # 马：日字走，蹩马腿
            if not ((abs(dr) == 2 and abs(dc) == 1) or (abs(dr) == 1 and abs(dc) == 2)):
                return False
            # 检查蹩马腿
            if abs(dr) == 2:
                leg_row = from_row + (1 if dr > 0 else -1)
                leg_col = from_col
            else:
                leg_row = from_row
                leg_col = from_col + (1 if dc > 0 else -1)
            if self.board[self._rc_to_pos(leg_row, leg_col)] != Piece.EMPTY:
                return False
            return True

        elif piece in (Piece.R_CHARIOT, Piece.B_CHARIOT):
            # 车：直线走
            if dr != 0 and dc != 0:
                return False
            if self._get_pieces_between(from_pos, to_pos) > 0:
                return False
            return True

        elif piece in (Piece.R_CANNON, Piece.B_CANNON):
            # 炮：直线走，隔子吃
            if dr != 0 and dc != 0:
                return False
            pieces_between = self._get_pieces_between(from_pos, to_pos)
            if target == Piece.EMPTY:
                # 不吃子时不能隔子
                return pieces_between == 0
            else:
                # 吃子时必须隔一子
                return pieces_between == 1

        elif piece in (Piece.R_SOLDIER, Piece.B_SOLDIER):
            # 兵/卒
            if side == Side.RED:
                # 红兵向上走
                if not self._is_across_river(from_row, side):
                    # 未过河：只能向前一步
                    return dr == 1 and dc == 0
                else:
                    # 过河：可前进或横走
                    if dr == 1 and dc == 0:
                        return True
                    if dr == 0 and abs(dc) == 1:
                        return True
                    return False
            else:
                # 黑卒向下走
                if not self._is_across_river(from_row, side):
                    # 未过河：只能向前一步
                    return dr == -1 and dc == 0
                else:
                    # 过河：可前进或横走
                    if dr == -1 and dc == 0:
                        return True
                    if dr == 0 and abs(dc) == 1:
                        return True
                    return False

        return False

    def _kings_facing(self) -> bool:
        """检查将帅是否对脸"""
        red_king_pos = self._find_king(Side.RED)
        black_king_pos = self._find_king(Side.BLACK)

        if red_king_pos is None or black_king_pos is None:
            return False

        red_row, red_col = self._pos_to_rc(red_king_pos)
        black_row, black_col = self._pos_to_rc(black_king_pos)

        if red_col != black_col:
            return False

        # 检查中间是否有棋子
        for r in range(red_row + 1, black_row):
            if self.board[self._rc_to_pos(r, red_col)] != Piece.EMPTY:
                return False

        return True

    def _is_in_check(self, side: Side) -> bool:
        """检查指定方是否被将军"""
        king_pos = self._find_king(side)
        if king_pos is None:
            return True  # 没有将/帅，算被将

        opponent = self._get_opponent(side)

        # 检查所有对方棋子是否能吃到将/帅
        for i, piece in enumerate(self.board):
            if get_piece_side(piece) == opponent:
                if self._is_valid_piece_move(i, king_pos):
                    return True

        # 检查将帅对脸
        if self._kings_facing():
            return True

        return False

    def _has_valid_move(self, side: Side) -> bool:
        """检查指定方是否有合法走法"""
        for from_pos, piece in enumerate(self.board):
            if get_piece_side(piece) != side:
                continue

            for to_pos in range(90):
                if self._is_valid_piece_move(from_pos, to_pos):
                    # 模拟走棋
                    original = self.board[to_pos]
                    self.board[to_pos] = piece
                    self.board[from_pos] = Piece.EMPTY

                    # 检查是否仍被将军或将帅对脸
                    still_in_check = self._is_in_check(side) or self._kings_facing()

                    # 还原
                    self.board[from_pos] = piece
                    self.board[to_pos] = original

                    if not still_in_check:
                        return True

        return False

    def make_move(self, player_id: str, from_pos: int, to_pos: int) -> Tuple[bool, str]:
        """
        走棋

        Args:
            player_id: 玩家 ID
            from_pos: 起始位置索引
            to_pos: 目标位置索引

        Returns:
            (是否成功, 消息)
        """
        if self.is_finished:
            return False, "游戏已结束"

        if self.player_black is None:
            return False, "等待对手加入"

        # 检查是否轮到该玩家
        if self.current_turn == Side.RED and player_id != self.player_red:
            return False, "现在是红方回合"
        if self.current_turn == Side.BLACK and player_id != self.player_black:
            return False, "现在是黑方回合"

        # 检查位置有效性
        if not (0 <= from_pos < 90 and 0 <= to_pos < 90):
            return False, "位置超出范围"

        piece = self.board[from_pos]
        if piece == Piece.EMPTY:
            return False, "起始位置没有棋子"

        # 检查是否是自己的棋子
        if get_piece_side(piece) != self.current_turn:
            return False, "只能移动自己的棋子"

        # 检查走法是否合法
        if not self._is_valid_piece_move(from_pos, to_pos):
            return False, "走法不合规则"

        # 模拟走棋，检查是否会被将军或将帅对脸
        target = self.board[to_pos]
        self.board[to_pos] = piece
        self.board[from_pos] = Piece.EMPTY

        if self._is_in_check(self.current_turn) or self._kings_facing():
            # 还原
            self.board[from_pos] = piece
            self.board[to_pos] = target
            return False, "走这步会被将军或将帅对脸"

        # 走棋成功，更新状态
        self.last_move = (from_pos, to_pos)
        self.move_count += 1

        # 切换回合
        opponent = self._get_opponent(self.current_turn)
        self.current_turn = opponent

        # 检查对方是否被将军
        self.in_check = self._is_in_check(opponent)

        # 检查是否将死
        if self.in_check and not self._has_valid_move(opponent):
            self.is_finished = True
            self.winner = self._get_opponent(opponent)
            return True, "将死！游戏结束"

        # 检查是否困毙（无子可动但未被将军）
        if not self.in_check and not self._has_valid_move(opponent):
            self.is_finished = True
            self.winner = self._get_opponent(opponent)
            return True, "困毙！游戏结束"

        msg = "走棋成功"
        if self.in_check:
            msg = "将军！"

        return True, msg

    def surrender(self, player_id: str) -> Tuple[bool, str]:
        """认输"""
        if self.is_finished:
            return False, "游戏已结束"

        if player_id == self.player_red:
            self.winner = Side.BLACK
            self.is_finished = True
            return True, "红方认输"
        elif player_id == self.player_black:
            self.winner = Side.RED
            self.is_finished = True
            return True, "黑方认输"
        else:
            return False, "你不是游戏参与者"

    def get_coordinate_label(self, pos: int) -> str:
        """获取位置的坐标标签"""
        row, col = self._pos_to_rc(pos)
        return f"{COLUMN_LABELS[col]}{row + 1}"

    def render_board(self) -> str:
        """渲染棋盘为文本"""
        lines = []

        # 列标签
        col_labels = "   " + "  ".join(COLUMN_LABELS)
        lines.append(col_labels)

        # 棋盘（从上往下，即 row 9 到 row 0）
        for row in range(9, -1, -1):
            row_num = str(row + 1).rjust(2)
            cells = []
            for col in range(9):
                piece = self.board[self._rc_to_pos(row, col)]
                cells.append(PIECE_NAMES[piece])
            line = f"{row_num} {' '.join(cells)} {row_num}"
            lines.append(line)

            # 楚河汉界
            if row == 5:
                lines.append("   ─────楚河  汉界─────")

        lines.append(col_labels)
        return "\n".join(lines)

    def get_status_text(self, player_names: Dict[str, str] = None) -> str:
        """获取游戏状态文本"""
        if player_names is None:
            player_names = {}

        red_name = player_names.get(self.player_red, self.player_red[:8])
        black_name = player_names.get(
            self.player_black,
            self.player_black[:8] if self.player_black else "等待加入"
        )

        lines = [
            "🎮 中国象棋",
            "━" * 25,
            "",
            self.render_board(),
            "",
        ]

        if self.is_finished:
            if self.winner == Side.RED:
                lines.append(f"🏆 红方 ({red_name}) 获胜！")
            elif self.winner == Side.BLACK:
                lines.append(f"🏆 黑方 ({black_name}) 获胜！")
            else:
                lines.append("🤝 游戏结束")
        else:
            if self.player_black is None:
                lines.append("⏳ 等待对手加入...")
                lines.append("发送 /加入象棋 参与游戏")
            else:
                turn_name = red_name if self.current_turn == Side.RED else black_name
                turn_text = "红方" if self.current_turn == Side.RED else "黑方"
                lines.append(f"👉 轮到 {turn_text} ({turn_name})")
                if self.in_check:
                    lines.append("⚠️ 将军！")
                lines.append("发送 /走棋 炮二平五 或 A1-A2")

        lines.extend([
            "",
            "━" * 25,
            f"🔴 红: {red_name}",
            f"⚫ 黑: {black_name}",
            f"📊 第 {self.move_count} 回合",
        ])

        if self.last_move:
            from_label = self.get_coordinate_label(self.last_move[0])
            to_label = self.get_coordinate_label(self.last_move[1])
            lines.append(f"📍 最后走子: {from_label}-{to_label}")

        return "\n".join(lines)


class XiangqiManager:
    """象棋游戏管理器"""

    def __init__(self):
        self._games: Dict[str, XiangqiGame] = {}

    def get_game(self, group_id: str) -> Optional[XiangqiGame]:
        """获取群内的游戏"""
        return self._games.get(group_id)

    def create_game(
        self, group_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[XiangqiGame]]:
        """创建新游戏"""
        existing = self._games.get(group_id)
        if existing and not existing.is_finished:
            return False, "当前群已有进行中的游戏", existing

        game = XiangqiGame(player_red=player_id)
        self._games[group_id] = game
        return True, "游戏创建成功，你是红方", game

    def join_game(
        self, group_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[XiangqiGame]]:
        """加入游戏"""
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        if game.is_finished:
            return False, "游戏已结束，请发起新游戏", None

        if game.player_black is not None:
            return False, "游戏已满员", game

        if not game.join(player_id):
            return False, "你已经在游戏中了", game

        return True, "加入成功，你是黑方！红方先行", game

    def make_move(
        self, group_id: str, player_id: str, move_str: str
    ) -> Tuple[bool, str, Optional[XiangqiGame]]:
        """走棋"""
        game = self._games.get(group_id)
        if not game:
            return False, "当前群没有进行中的游戏", None

        # 解析走法
        move = game.parse_move(move_str)
        if move is None:
            return False, "走法格式错误，请使用如 炮二进四 或 E1-E2 的格式", None

        from_pos, to_pos = move
        success, msg = game.make_move(player_id, from_pos, to_pos)
        return success, msg, game

    def surrender(
        self, group_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[XiangqiGame]]:
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
