# -*- coding: utf-8 -*-
"""
游戏图片渲染服务客户端
"""
import aiohttp
import os
import tempfile
from typing import Optional, Dict, List, Tuple

from astrbot.api import logger


class GameRenderer:
    """游戏图片渲染服务"""

    def __init__(self, service_url: str = "http://172.17.0.1:51234"):
        self.service_url = service_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def render_tictactoe(
        self,
        board: List[str],
        player_x_name: str,
        player_o_name: Optional[str],
        current_turn: str,
        winner: Optional[str],
        is_finished: bool,
        subtitle: str = ""
    ) -> Optional[str]:
        """
        渲染井字棋游戏状态为图片

        Args:
            board: 棋盘状态，9个元素的列表，'X', 'O' 或 ''
            player_x_name: X 方玩家名称
            player_o_name: O 方玩家名称（可为空）
            current_turn: 当前回合，'X' 或 'O'
            winner: 获胜方，'X', 'O' 或 None
            is_finished: 游戏是否结束
            subtitle: 副标题

        Returns:
            保存的图片路径，失败返回 None
        """
        payload = {
            "board": board,
            "player_x_name": player_x_name,
            "player_o_name": player_o_name or "",
            "current_turn": current_turn,
            "winner": winner,
            "is_finished": is_finished,
            "subtitle": subtitle
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.service_url}/api/tictactoe",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        temp_dir = tempfile.gettempdir()
                        img_path = os.path.join(temp_dir, f"tictactoe_{os.getpid()}.png")

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        logger.info(f"井字棋图片已保存: {img_path}")
                        return img_path
                    else:
                        logger.error(f"渲染服务返回错误: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"调用渲染服务失败: {e}")
            return None

    async def render_go(
        self,
        board: List[str],
        board_size: int,
        black_player_name: str,
        white_player_name: Optional[str],
        current_turn: str,
        captured_black: int = 0,
        captured_white: int = 0,
        move_count: int = 0,
        last_move: Optional[int] = None,
        winner: Optional[str] = None,
        is_finished: bool = False,
        subtitle: str = ""
    ) -> Optional[str]:
        """
        渲染围棋游戏状态为图片

        Args:
            board: 棋盘状态，board_size*board_size 个元素，'B', 'W' 或 ''
            board_size: 棋盘大小 (9, 13, 19)
            black_player_name: 黑方玩家名称
            white_player_name: 白方玩家名称（可为空）
            current_turn: 当前回合，'B' 或 'W'
            captured_black: 黑方被提子数
            captured_white: 白方被提子数
            move_count: 总步数
            last_move: 最后落子位置索引
            winner: 获胜方，'B', 'W' 或 None
            is_finished: 游戏是否结束
            subtitle: 副标题

        Returns:
            保存的图片路径，失败返回 None
        """
        payload = {
            "board": board,
            "board_size": board_size,
            "black_player_name": black_player_name,
            "player_white_name": white_player_name or "",
            "current_turn": current_turn,
            "captured_black": captured_black,
            "captured_white": captured_white,
            "move_count": move_count,
            "last_move": last_move,
            "is_finished": is_finished,
            "winner": winner,
            "subtitle": subtitle
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.service_url}/api/go",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        temp_dir = tempfile.gettempdir()
                        img_path = os.path.join(temp_dir, f"go_{os.getpid()}.png")

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        logger.info(f"围棋图片已保存: {img_path}")
                        return img_path
                    else:
                        logger.error(f"渲染服务返回错误: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"调用渲染服务失败: {e}")
            return None

    async def render_gomoku(
        self,
        board: List[str],
        board_size: int,
        black_player_name: str,
        white_player_name: Optional[str],
        current_turn: str,
        move_count: int = 0,
        last_move: Optional[int] = None,
        win_line: Optional[List[int]] = None,
        winner: Optional[str] = None,
        is_finished: bool = False,
        subtitle: str = ""
    ) -> Optional[str]:
        """
        渲染五子棋游戏状态为图片

        Args:
            board: 棋盘状态，board_size*board_size 个元素，'B', 'W' 或 ''
            board_size: 棋盘大小 (13, 15, 19)
            black_player_name: 黑方玩家名称
            white_player_name: 白方玩家名称（可为空）
            current_turn: 当前回合，'B' 或 'W'
            move_count: 总步数
            last_move: 最后落子位置索引
            win_line: 获胜连线位置列表
            winner: 获胜方，'B', 'W' 或 None
            is_finished: 游戏是否结束
            subtitle: 副标题

        Returns:
            保存的图片路径，失败返回 None
        """
        payload = {
            "board": board,
            "board_size": board_size,
            "black_player_name": black_player_name,
            "white_player_name": white_player_name or "",
            "current_turn": current_turn,
            "move_count": move_count,
            "last_move": last_move,
            "win_line": win_line,
            "is_finished": is_finished,
            "winner": winner,
            "subtitle": subtitle
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.service_url}/api/gomoku",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        temp_dir = tempfile.gettempdir()
                        img_path = os.path.join(temp_dir, f"gomoku_{os.getpid()}.png")

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        logger.info(f"五子棋图片已保存: {img_path}")
                        return img_path
                    else:
                        logger.error(f"渲染服务返回错误: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"调用渲染服务失败: {e}")
            return None

    async def render_xiangqi(
        self,
        board: List[str],
        red_player_name: str,
        black_player_name: Optional[str],
        current_turn: str,
        move_count: int = 0,
        last_move: Optional[Tuple[int, int]] = None,
        in_check: bool = False,
        winner: Optional[str] = None,
        is_finished: bool = False,
        subtitle: str = ""
    ) -> Optional[str]:
        """
        渲染象棋游戏状态为图片

        Args:
            board: 棋盘状态，90 个元素，棋子代码或 ''
            red_player_name: 红方玩家名称
            black_player_name: 黑方玩家名称（可为空）
            current_turn: 当前回合，'R' 或 'B'
            move_count: 总回合数
            last_move: 最后走子 (from_pos, to_pos)
            in_check: 是否将军
            winner: 获胜方，'R', 'B' 或 None
            is_finished: 游戏是否结束
            subtitle: 副标题

        Returns:
            保存的图片路径，失败返回 None
        """
        payload = {
            "board": board,
            "red_player_name": red_player_name,
            "black_player_name": black_player_name or "",
            "current_turn": current_turn,
            "move_count": move_count,
            "last_move": {"from": last_move[0], "to": last_move[1]} if last_move else None,
            "in_check": in_check,
            "is_finished": is_finished,
            "winner": winner,
            "subtitle": subtitle
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.service_url}/api/xiangqi",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        temp_dir = tempfile.gettempdir()
                        img_path = os.path.join(temp_dir, f"xiangqi_{os.getpid()}.png")

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        logger.info(f"象棋图片已保存: {img_path}")
                        return img_path
                    else:
                        logger.error(f"渲染服务返回错误: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"调用渲染服务失败: {e}")
            return None

    async def render_game_help(
        self,
        subtitle: str = ""
    ) -> Optional[str]:
        """
        渲染游戏帮助图片

        Args:
            subtitle: 副标题

        Returns:
            保存的图片路径，失败返回 None
        """
        payload = {
            "subtitle": subtitle
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.service_url}/api/gamehelp",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        temp_dir = tempfile.gettempdir()
                        img_path = os.path.join(temp_dir, f"gamehelp_{os.getpid()}.png")

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        logger.info(f"游戏帮助图片已保存: {img_path}")
                        return img_path
                    else:
                        logger.error(f"渲染服务返回错误: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"调用渲染服务失败: {e}")
            return None

    async def render_junqi(
        self,
        board: List[dict],
        player_a_name: str,
        player_b_name: Optional[str],
        player_a_side: Optional[str],
        player_b_side: Optional[str],
        current_turn: int,
        move_count: int = 0,
        last_action: Optional[str] = None,
        last_pos: Optional[int] = None,
        is_finished: bool = False,
        winner: Optional[str] = None,
        subtitle: str = ""
    ) -> Optional[str]:
        """
        渲染军棋游戏状态为图片

        Args:
            board: 棋盘数据
            player_a_name: 玩家A名称
            player_b_name: 玩家B名称
            player_a_side: 玩家A阵营
            player_b_side: 玩家B阵营
            current_turn: 当前回合 (1=玩家A, 2=玩家B)
            move_count: 步数
            last_action: 最后操作描述
            last_pos: 最后操作位置
            is_finished: 游戏是否结束
            winner: 获胜者
            subtitle: 副标题

        Returns:
            保存的图片路径，失败返回 None
        """
        payload = {
            "board": board,
            "player_a_name": player_a_name,
            "player_b_name": player_b_name or "",
            "player_a_side": player_a_side,
            "player_b_side": player_b_side,
            "current_turn": current_turn,
            "move_count": move_count,
            "last_action": last_action,
            "last_pos": last_pos,
            "is_finished": is_finished,
            "winner": winner,
            "subtitle": subtitle
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.service_url}/api/junqi",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        temp_dir = tempfile.gettempdir()
                        img_path = os.path.join(temp_dir, f"junqi_{os.getpid()}.png")

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        logger.info(f"军棋图片已保存: {img_path}")
                        return img_path
                    else:
                        logger.error(f"渲染服务返回错误: {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"调用渲染服务失败: {e}")
            return None
