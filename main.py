# -*- coding: utf-8 -*-
"""
AstrBot 小游戏合集插件
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

from .games.tictactoe import TicTacToeManager, Player
from .games.go import GoManager, Stone
from .games.xiangqi import XiangqiManager, Side, PIECE_CODES
from .games.gomoku import GomokuManager, Stone as GomokuStone
from .games.junqi import JunqiManager, Side as JunqiSide
from .services.image_renderer import GameRenderer

# 尝试导入 APScheduler
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("APScheduler 未安装，超时功能将不可用")


@register("game", "riddle", "QQ 群小游戏合集", "1.0.0")
class GamePlugin(Star):
    """小游戏合集插件"""

    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config if config else {}

        # 初始化游戏管理器
        self.ttt = TicTacToeManager()
        self.go = GoManager()
        self.xiangqi = XiangqiManager()
        self.gomoku = GomokuManager()
        self.junqi = JunqiManager()

        # 初始化图片渲染服务
        render_url = self.config.get("render_service_url", "http://172.17.0.1:51234")
        self.renderer = GameRenderer(render_url)

        # 缓存玩家昵称 player_id -> name
        self._player_names: dict = {}

        # 存储每个群的最后消息 ID，用于撤回
        # group_id -> message_id
        self._last_msg_ids: Dict[str, int] = {}

        # 存储每个群的 unified_msg_origin，用于主动发消息
        self._group_umo: Dict[str, any] = {}

        # 存储每个群的 bot client，用于撤回
        self._group_bots: Dict[str, any] = {}

        # 超时调度器
        self._scheduler = None
        if HAS_APSCHEDULER:
            self._scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
            self._scheduler.start()

        # 超时时间（秒）
        self._timeout_seconds = self.config.get("turn_timeout_seconds", 60)
        # 等待加入超时（秒）
        self._join_timeout_seconds = self.config.get("join_timeout_seconds", 60)

        logger.info("小游戏插件已加载")

    async def _recall_last_message(self, group_id: str, bot):
        """撤回上一条游戏消息"""
        msg_id = self._last_msg_ids.get(group_id)
        if msg_id and bot:
            try:
                await bot.api.call_action('delete_msg', message_id=msg_id)
                logger.info(f"已撤回消息: {msg_id}")
            except Exception as e:
                logger.debug(f"撤回消息失败: {e}")
            self._last_msg_ids.pop(group_id, None)

    async def _send_image_and_save_id(self, group_id: str, img_path: str, bot) -> bool:
        """主动发送图片并保存消息ID用于撤回"""
        if not bot:
            logger.debug("bot 客户端不存在，无法发送图片")
            return False
        try:
            import base64
            # 读取图片并转换为 base64，避免 Docker 跨容器路径访问问题
            with open(img_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            
            # 使用 send_group_msg API 发送 base64 图片
            result = await bot.api.call_action(
                'send_group_msg',
                group_id=int(group_id),
                message=[{"type": "image", "data": {"file": f"base64://{img_data}"}}]
            )
            if result and 'message_id' in result:
                self._last_msg_ids[group_id] = result['message_id']
                logger.info(f"保存消息 ID: {result['message_id']}")
            return True
        except Exception as e:
            logger.error(f"发送图片失败: {e}")
            return False

    def _save_bot_client(self, event: AstrMessageEvent):
        """保存 bot client 用于撤回"""
        group_id = str(event.get_group_id())
        if event.get_platform_name() == "aiocqhttp":
            try:
                from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent
                if isinstance(event, AiocqhttpMessageEvent):
                    self._group_bots[group_id] = event.bot
                    self._group_umo[group_id] = event.unified_msg_origin
            except Exception:
                pass

    def _schedule_timeout(self, group_id: str, game_type: str):
        """设置走棋超时定时器"""
        if not self._scheduler or not self._timeout_seconds:
            return

        job_id = f"timeout_{group_id}"

        # 取消旧的定时器
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

        # 添加新的定时器
        self._scheduler.add_job(
            self._handle_timeout,
            'date',
            run_date=datetime.now() + timedelta(seconds=self._timeout_seconds),
            args=[group_id, game_type],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=30
        )

    def _schedule_join_timeout(self, group_id: str, game_type: str):
        """设置等待加入超时定时器"""
        if not self._scheduler or not self._join_timeout_seconds:
            return

        job_id = f"join_timeout_{group_id}"

        # 取消旧的定时器
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

        # 添加新的定时器
        self._scheduler.add_job(
            self._handle_join_timeout,
            'date',
            run_date=datetime.now() + timedelta(seconds=self._join_timeout_seconds),
            args=[group_id, game_type],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=30
        )

    def _cancel_timeout(self, group_id: str):
        """取消超时定时器"""
        if not self._scheduler:
            return
        try:
            self._scheduler.remove_job(f"timeout_{group_id}")
        except Exception:
            pass

    def _cancel_join_timeout(self, group_id: str):
        """取消加入超时定时器"""
        if not self._scheduler:
            return
        try:
            self._scheduler.remove_job(f"join_timeout_{group_id}")
        except Exception:
            pass

    async def _handle_timeout(self, group_id: str, game_type: str):
        """处理走棋超时"""
        logger.info(f"游戏超时: {group_id}, 类型: {game_type}")

        if game_type == "ttt":
            game = self.ttt.get_game(group_id)
            if game and not game.is_finished and game.player_o:
                current_player = game.player_x if game.current_turn == Player.X else game.player_o
                game.surrender(current_player)
                await self._send_timeout_result(group_id, game_type, current_player)

        elif game_type == "go":
            game = self.go.get_game(group_id)
            if game and not game.is_finished and game.player_white:
                current_player = game.player_black if game.current_turn == Stone.BLACK else game.player_white
                game.surrender(current_player)
                await self._send_timeout_result(group_id, game_type, current_player)

        elif game_type == "xiangqi":
            game = self.xiangqi.get_game(group_id)
            if game and not game.is_finished and game.player_black:
                current_player = game.player_red if game.current_turn == Side.RED else game.player_black
                game.surrender(current_player)
                await self._send_timeout_result(group_id, game_type, current_player)

        elif game_type == "gomoku":
            game = self.gomoku.get_game(group_id)
            if game and not game.is_finished and game.player_white:
                current_player = game.player_black if game.current_turn == GomokuStone.BLACK else game.player_white
                game.surrender(current_player)
                await self._send_timeout_result(group_id, game_type, current_player)

    async def _handle_join_timeout(self, group_id: str, game_type: str):
        """处理等待加入超时"""
        logger.info(f"等待加入超时: {group_id}, 类型: {game_type}")

        bot = self._group_bots.get(group_id)
        umo = self._group_umo.get(group_id)

        # 检查游戏是否仍在等待加入
        should_close = False
        if game_type == "ttt":
            game = self.ttt.get_game(group_id)
            if game and not game.is_finished and game.player_o is None:
                self.ttt.end_game(group_id)
                should_close = True
        elif game_type == "go":
            game = self.go.get_game(group_id)
            if game and not game.is_finished and game.player_white is None:
                self.go.end_game(group_id)
                should_close = True
        elif game_type == "xiangqi":
            game = self.xiangqi.get_game(group_id)
            if game and not game.is_finished and game.player_black is None:
                self.xiangqi.end_game(group_id)
                should_close = True
        elif game_type == "gomoku":
            game = self.gomoku.get_game(group_id)
            if game and not game.is_finished and game.player_white is None:
                self.gomoku.end_game(group_id)
                should_close = True

        if should_close:
            # 撤回消息
            await self._recall_last_message(group_id, bot)

            # 发送超时通知
            if umo:
                from astrbot.api.event import MessageChain
                msg = MessageChain().message("⏰ 无人加入，游戏已自动取消")
                await self.context.send_message(umo, msg)

            # 清理消息 ID
            self._last_msg_ids.pop(group_id, None)

    async def _send_timeout_result(self, group_id: str, game_type: str, timeout_player: str):
        """发送超时结果"""
        umo = self._group_umo.get(group_id)
        bot = self._group_bots.get(group_id)

        if not umo:
            return

        # 撤回旧消息
        await self._recall_last_message(group_id, bot)

        player_name = self._player_names.get(timeout_player, timeout_player[:8])

        # 发送超时通知
        from astrbot.api.event import MessageChain
        timeout_msg = MessageChain().message(f"⏰ {player_name} 思考超时，自动认输！")
        await self.context.send_message(umo, timeout_msg)

        # 发送最终棋盘
        if game_type == "ttt":
            game = self.ttt.get_game(group_id)
            if game:
                await self._send_game_image_direct(group_id, game_type, game)
        elif game_type == "go":
            game = self.go.get_game(group_id)
            if game:
                await self._send_game_image_direct(group_id, game_type, game)
        elif game_type == "xiangqi":
            game = self.xiangqi.get_game(group_id)
            if game:
                await self._send_game_image_direct(group_id, game_type, game)
        elif game_type == "gomoku":
            game = self.gomoku.get_game(group_id)
            if game:
                await self._send_game_image_direct(group_id, game_type, game)

    async def _send_game_image_direct(self, group_id: str, game_type: str, game):
        """直接发送游戏图片（不通过 yield）"""
        umo = self._group_umo.get(group_id)
        if not umo:
            return

        from astrbot.api.event import MessageChain

        if game_type == "ttt":
            board = ["X" if c == Player.X else ("O" if c == Player.O else "") for c in game.board]
            x_name = self._player_names.get(game.player_x, game.player_x[:8])
            o_name = self._player_names.get(game.player_o, game.player_o[:8] if game.player_o else "")
            img_path = await self.renderer.render_tictactoe(
                board=board,
                player_x_name=x_name,
                player_o_name=o_name,
                current_turn="X" if game.current_turn == Player.X else "O",
                winner="X" if game.winner == Player.X else ("O" if game.winner == Player.O else None),
                is_finished=game.is_finished,
                subtitle="游戏结束"
            )
        elif game_type == "go":
            board = ["B" if c == Stone.BLACK else ("W" if c == Stone.WHITE else "") for c in game.board]
            black_name = self._player_names.get(game.player_black, game.player_black[:8])
            white_name = self._player_names.get(game.player_white, game.player_white[:8] if game.player_white else "")
            img_path = await self.renderer.render_go(
                board=board,
                board_size=game.board_size,
                black_player_name=black_name,
                white_player_name=white_name,
                current_turn="B" if game.current_turn == Stone.BLACK else "W",
                captured_black=game.captured_black,
                captured_white=game.captured_white,
                move_count=game.move_count,
                last_move=game.last_move,
                winner="B" if game.winner == Stone.BLACK else ("W" if game.winner == Stone.WHITE else None),
                is_finished=game.is_finished,
                subtitle="游戏结束"
            )
        elif game_type == "xiangqi":
            board = [PIECE_CODES[p] for p in game.board]
            red_name = self._player_names.get(game.player_red, game.player_red[:8])
            black_name = self._player_names.get(game.player_black, game.player_black[:8] if game.player_black else "")
            img_path = await self.renderer.render_xiangqi(
                board=board,
                red_player_name=red_name,
                black_player_name=black_name,
                current_turn="R" if game.current_turn == Side.RED else "B",
                move_count=game.move_count,
                last_move=game.last_move,
                in_check=game.in_check,
                winner="R" if game.winner == Side.RED else ("B" if game.winner == Side.BLACK else None),
                is_finished=game.is_finished,
                subtitle="游戏结束"
            )
        elif game_type == "gomoku":
            board = ["B" if c == GomokuStone.BLACK else ("W" if c == GomokuStone.WHITE else "") for c in game.board]
            black_name = self._player_names.get(game.player_black, game.player_black[:8])
            white_name = self._player_names.get(game.player_white, game.player_white[:8] if game.player_white else "")
            img_path = await self.renderer.render_gomoku(
                board=board,
                board_size=game.board_size,
                black_player_name=black_name,
                white_player_name=white_name,
                current_turn="B" if game.current_turn == GomokuStone.BLACK else "W",
                move_count=game.move_count,
                last_move=game.last_move,
                win_line=game.win_line,
                winner="B" if game.winner == GomokuStone.BLACK else ("W" if game.winner == GomokuStone.WHITE else None),
                is_finished=game.is_finished,
                subtitle="游戏结束"
            )
        else:
            return

        if img_path:
            chain = MessageChain().file_image(img_path)
            await self.context.send_message(umo, chain)

    async def _render_and_send(self, group_id: str, game_type: str, game, event: AstrMessageEvent):
        """渲染并发送游戏图片，自动撤回上一张"""
        bot = self._group_bots.get(group_id)

        # 撤回上一条消息
        await self._recall_last_message(group_id, bot)

        # 渲染图片
        img_path = None
        fallback_text = None
        
        if game_type == "ttt":
            img_path, fallback_text = await self._get_ttt_render(game)
        elif game_type == "go":
            img_path, fallback_text = await self._get_go_render(game)
        elif game_type == "xiangqi":
            img_path, fallback_text = await self._get_xiangqi_render(game)
        elif game_type == "gomoku":
            img_path, fallback_text = await self._get_gomoku_render(game)

        # 发送图片（优先使用主动发送以获取消息ID）
        if img_path and bot:
            sent = await self._send_image_and_save_id(group_id, img_path, bot)
            if not sent:
                # 主动发送失败，fallback 到被动发送
                yield event.image_result(img_path)
        elif img_path:
            # 没有 bot 客户端，使用被动发送
            yield event.image_result(img_path)
        elif fallback_text:
            yield event.plain_result(fallback_text)

        # 管理超时
        if game_type == "ttt":
            if game.is_finished:
                self._cancel_timeout(group_id)
                self._cancel_join_timeout(group_id)
            elif game.player_o:
                self._cancel_join_timeout(group_id)
                self._schedule_timeout(group_id, "ttt")
            else:
                self._schedule_join_timeout(group_id, "ttt")
        elif game_type == "go":
            if game.is_finished:
                self._cancel_timeout(group_id)
                self._cancel_join_timeout(group_id)
            elif game.player_white:
                self._cancel_join_timeout(group_id)
                self._schedule_timeout(group_id, "go")
            else:
                self._schedule_join_timeout(group_id, "go")
        elif game_type == "xiangqi":
            if game.is_finished:
                self._cancel_timeout(group_id)
                self._cancel_join_timeout(group_id)
            elif game.player_black:
                self._cancel_join_timeout(group_id)
                self._schedule_timeout(group_id, "xiangqi")
            else:
                self._schedule_join_timeout(group_id, "xiangqi")
        elif game_type == "gomoku":
            if game.is_finished:
                self._cancel_timeout(group_id)
                self._cancel_join_timeout(group_id)
            elif game.player_white:
                self._cancel_join_timeout(group_id)
                self._schedule_timeout(group_id, "gomoku")
            else:
                self._schedule_join_timeout(group_id, "gomoku")

    async def _get_ttt_render(self, game):
        """渲染井字棋游戏状态，返回 (img_path, fallback_text)"""
        board = ["X" if c == Player.X else ("O" if c == Player.O else "") for c in game.board]
        x_name = self._player_names.get(game.player_x, game.player_x[:8])
        o_name = self._player_names.get(game.player_o, game.player_o[:8] if game.player_o else "")
        moves = sum(1 for c in board if c)
        subtitle = f"第 {moves} 步" if moves > 0 else "游戏开始"

        img_path = await self.renderer.render_tictactoe(
            board=board,
            player_x_name=x_name,
            player_o_name=o_name,
            current_turn="X" if game.current_turn == Player.X else "O",
            winner="X" if game.winner == Player.X else ("O" if game.winner == Player.O else None),
            is_finished=game.is_finished,
            subtitle=subtitle
        )

        if img_path:
            return img_path, None
        else:
            return None, game.get_status_text(self._player_names)

    async def _render_ttt_game(self, game, event: AstrMessageEvent):
        """渲染井字棋游戏状态并返回图片或文本（兼容旧调用）"""
        img_path, fallback_text = await self._get_ttt_render(game)
        if img_path:
            yield event.image_result(img_path)
        else:
            yield event.plain_result(fallback_text)

    async def _get_go_render(self, game):
        """渲染围棋游戏状态，返回 (img_path, fallback_text)"""
        board = ["B" if c == Stone.BLACK else ("W" if c == Stone.WHITE else "") for c in game.board]
        black_name = self._player_names.get(game.player_black, game.player_black[:8])
        white_name = self._player_names.get(game.player_white, game.player_white[:8] if game.player_white else "")
        subtitle = f"第 {game.move_count} 手" if game.move_count > 0 else "游戏开始"

        img_path = await self.renderer.render_go(
            board=board,
            board_size=game.board_size,
            black_player_name=black_name,
            white_player_name=white_name,
            current_turn="B" if game.current_turn == Stone.BLACK else "W",
            captured_black=game.captured_black,
            captured_white=game.captured_white,
            move_count=game.move_count,
            last_move=game.last_move,
            winner="B" if game.winner == Stone.BLACK else ("W" if game.winner == Stone.WHITE else None),
            is_finished=game.is_finished,
            subtitle=subtitle
        )

        if img_path:
            return img_path, None
        else:
            return None, game.get_status_text(self._player_names)

    async def _render_go_game(self, game, event: AstrMessageEvent):
        """渲染围棋游戏状态并返回图片或文本（兼容旧调用）"""
        img_path, fallback_text = await self._get_go_render(game)
        if img_path:
            yield event.image_result(img_path)
        else:
            yield event.plain_result(fallback_text)

    async def _get_xiangqi_render(self, game):
        """渲染象棋游戏状态，返回 (img_path, fallback_text)"""
        board = [PIECE_CODES[p] for p in game.board]
        red_name = self._player_names.get(game.player_red, game.player_red[:8])
        black_name = self._player_names.get(game.player_black, game.player_black[:8] if game.player_black else "")
        subtitle = f"第 {game.move_count} 回合" if game.move_count > 0 else "游戏开始"

        img_path = await self.renderer.render_xiangqi(
            board=board,
            red_player_name=red_name,
            black_player_name=black_name,
            current_turn="R" if game.current_turn == Side.RED else "B",
            move_count=game.move_count,
            last_move=game.last_move,
            in_check=game.in_check,
            winner="R" if game.winner == Side.RED else ("B" if game.winner == Side.BLACK else None),
            is_finished=game.is_finished,
            subtitle=subtitle
        )

        if img_path:
            return img_path, None
        else:
            return None, game.get_status_text(self._player_names)

    async def _render_xiangqi_game(self, game, event: AstrMessageEvent):
        """渲染象棋游戏状态并返回图片或文本（兼容旧调用）"""
        img_path, fallback_text = await self._get_xiangqi_render(game)
        if img_path:
            yield event.image_result(img_path)
        else:
            yield event.plain_result(fallback_text)

    async def _get_gomoku_render(self, game):
        """渲染五子棋游戏状态，返回 (img_path, fallback_text)"""
        board = ["B" if c == GomokuStone.BLACK else ("W" if c == GomokuStone.WHITE else "") for c in game.board]
        black_name = self._player_names.get(game.player_black, game.player_black[:8])
        white_name = self._player_names.get(game.player_white, game.player_white[:8] if game.player_white else "")
        subtitle = f"第 {game.move_count} 手" if game.move_count > 0 else "游戏开始"

        img_path = await self.renderer.render_gomoku(
            board=board,
            board_size=game.board_size,
            black_player_name=black_name,
            white_player_name=white_name,
            current_turn="B" if game.current_turn == GomokuStone.BLACK else "W",
            move_count=game.move_count,
            last_move=game.last_move,
            win_line=game.win_line,
            winner="B" if game.winner == GomokuStone.BLACK else ("W" if game.winner == GomokuStone.WHITE else None),
            is_finished=game.is_finished,
            subtitle=subtitle
        )

        if img_path:
            return img_path, None
        else:
            return None, game.get_status_text(self._player_names)

    async def _render_gomoku_game(self, game, event: AstrMessageEvent):
        """渲染五子棋游戏状态并返回图片或文本（兼容旧调用）"""
        img_path, fallback_text = await self._get_gomoku_render(game)
        if img_path:
            yield event.image_result(img_path)
        else:
            yield event.plain_result(fallback_text)

    # ========== 消息监听与简化指令 ==========

    async def _execute_handler(self, handler_gen, event: AstrMessageEvent):
        """执行命令处理器并发送结果"""
        try:
            async for result in handler_gen:
                if result and hasattr(result, "chain") and result.chain:
                    await self.context.send_message(event.unified_msg_origin, result.chain)
                elif result and hasattr(result, "msg") and result.msg:
                    # 某些 Result 对象可能有 msg 属性
                    from astrbot.api.event import MessageChain
                    await self.context.send_message(event.unified_msg_origin, MessageChain().message(result.msg))
        except Exception as e:
            logger.error(f"处理简化指令失败: {e}")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """监听群消息，处理简化指令"""
        group_id = str(event.get_group_id())
        message = event.message_str.strip()
        sender_id = event.get_sender_id()

        # 1. 井字棋 (TicTacToe)
        ttt_game = self.ttt.get_game(group_id)
        if ttt_game and not ttt_game.is_finished:
            current_player = ttt_game.player_x if ttt_game.current_turn == Player.X else ttt_game.player_o
            if current_player == sender_id:
                # 支持数字 1-9
                if message.isdigit() and 1 <= int(message) <= 9:
                    num = int(message)
                    # 转换为 1-9 的字符串直接传给 ttt_move (假设 ttt_move 内部支持，或我们需要在此转换)
                    # ttt_move 目前只支持位置索引，还是需要转换一下？
                    # 之前的 ttt_move 实现似乎接受 user input "5"，然后转为 int。
                    # 所以直接传 message 即可。
                    await self._execute_handler(self.ttt_move(event, message), event)
                    return

        # 2. 五子棋 (Gomoku)
        gomoku_game = self.gomoku.get_game(group_id)
        if gomoku_game and not gomoku_game.is_finished:
            is_black = gomoku_game.current_turn == GomokuStone.BLACK
            current_player = gomoku_game.player_black if is_black else gomoku_game.player_white
            if current_player == sender_id:
                import re
                # 坐标 H8 或 8 8
                if re.match(r'^[A-Oa-o]\d{1,2}$', message) or re.match(r'^\d{1,2}[,\s]\d{1,2}$', message):
                    await self._execute_handler(self.gomoku_move(event, message), event)
                    return

        # 3. 围棋 (Go)
        go_game = self.go.get_game(group_id)
        if go_game and not go_game.is_finished:
            is_black = go_game.current_turn == Stone.BLACK
            current_player = go_game.player_black if is_black else go_game.player_white
            if current_player == sender_id:
                import re
                # 坐标 C3
                if re.match(r'^[A-Ta-t]\d{1,2}$', message):
                    await self._execute_handler(self.go_move(event, message), event)
                    return

        # 4. 象棋 (Xiangqi)
        xq_game = self.xiangqi.get_game(group_id)
        if xq_game and not xq_game.is_finished:
            is_red = xq_game.current_turn == Side.RED
            current_player = xq_game.player_red if is_red else xq_game.player_black
            if current_player == sender_id:
                # 中式记谱法 (炮二平五)
                if len(message) == 4 and message[0] in "车马相仕帅炮兵将士象馬車砲卒前后中":
                    await self._execute_handler(self.xiangqi_move(event, message), event)
                    return
                # 坐标 E1E2 (可能无分隔符) 或 E1-E2
                import re
                if re.match(r'^[A-Ia-i]\d\d?[-:>\s]?[A-Ia-i]\d\d?$', message):
                    await self._execute_handler(self.xiangqi_move(event, message), event)
                    return

        # 5. 军棋 (Junqi)
        junqi_game = self.junqi.get_game(group_id)
        if junqi_game and not junqi_game.is_finished:
            current_turn = junqi_game.current_turn
            current_player = junqi_game.player_a if current_turn == 1 else junqi_game.player_b
            if current_player == sender_id:
                import re
                # 翻棋 A1
                if re.match(r'^[A-Fa-f](?:10|[1-9])$', message):
                    await self._execute_handler(self.junqi_flip(event, message), event)
                    return
                # 移动 A1A2 或 A1-A2
                if re.match(r'^[A-Fa-f](?:10|[1-9])[->\s]?[A-Fa-f](?:10|[1-9])$', message):
                    await self._execute_handler(self.junqi_move(event, message), event)
                    return

    # ========== 井字棋 ==========

    @filter.command("井字棋", alias={"ttt", "tictactoe", "开始井字棋"})
    async def ttt_start(self, event: AstrMessageEvent):
        """发起一局井字棋。用法：/井字棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 井字棋仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        # 检查是否有其他游戏进行中
        if self._has_active_game(group_id):
            yield event.plain_result("❌ 当前群有进行中的游戏\n发送 /结束游戏 可强制结束")
            return

        success, msg, game = self.ttt.create_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}\n发送 /结束游戏 可强制结束当前游戏")
            return

        async for result in self._render_and_send(group_id, "ttt", game, event):
            yield result

    @filter.command("加入井字棋", alias={"jointtt", "加入游戏", "join"})
    async def ttt_join(self, event: AstrMessageEvent):
        """加入一局井字棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.ttt.join_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "ttt", game, event):
            yield result

    @filter.command("下棋", alias={"move", "m"})
    async def ttt_move(self, event: AstrMessageEvent, pos: str = None):
        """下棋落子。用法：/下棋 5（数字1-9对应棋盘位置）"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        if not pos:
            yield event.plain_result("❌ 请指定位置（1-9），例如：/下棋 5")
            return

        try:
            position = int(pos)
        except ValueError:
            yield event.plain_result("❌ 位置必须是数字（1-9）")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.ttt.make_move(group_id, player_id, position)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "ttt", game, event):
            yield result

    @filter.command("认输", alias={"surrender", "投降"})
    async def game_surrender(self, event: AstrMessageEvent):
        """认输"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        self._save_bot_client(event)

        # 尝试井字棋
        game = self.ttt.get_game(group_id)
        if game and not game.is_finished:
            success, msg, game = self.ttt.surrender(group_id, player_id)
            if not success:
                yield event.plain_result(f"❌ {msg}")
                return
            self._cancel_timeout(group_id)
            async for result in self._render_and_send(group_id, "ttt", game, event):
                yield result
            return

        # 尝试围棋
        go_game = self.go.get_game(group_id)
        if go_game and not go_game.is_finished:
            success, msg, go_game = self.go.surrender(group_id, player_id)
            if not success:
                yield event.plain_result(f"❌ {msg}")
                return
            self._cancel_timeout(group_id)
            async for result in self._render_and_send(group_id, "go", go_game, event):
                yield result
            return

        # 尝试象棋
        xiangqi_game = self.xiangqi.get_game(group_id)
        if xiangqi_game and not xiangqi_game.is_finished:
            success, msg, xiangqi_game = self.xiangqi.surrender(group_id, player_id)
            if not success:
                yield event.plain_result(f"❌ {msg}")
                return
            self._cancel_timeout(group_id)
            async for result in self._render_and_send(group_id, "xiangqi", xiangqi_game, event):
                yield result
            return

        # 尝试五子棋
        gomoku_game = self.gomoku.get_game(group_id)
        if gomoku_game and not gomoku_game.is_finished:
            success, msg, gomoku_game = self.gomoku.surrender(group_id, player_id)
            if not success:
                yield event.plain_result(f"❌ {msg}")
                return
            self._cancel_timeout(group_id)
            async for result in self._render_and_send(group_id, "gomoku", gomoku_game, event):
                yield result
            return

        # 尝试军棋
        junqi_game = self.junqi.get_game(group_id)
        if junqi_game and not junqi_game.is_finished:
            success, msg, junqi_game = self.junqi.surrender(group_id, player_id)
            if not success:
                yield event.plain_result(f"❌ {msg}")
                return
            self._cancel_timeout(group_id)
            async for result in self._render_junqi_game(junqi_game, event):
                yield result
            return

        yield event.plain_result("❌ 当前群没有进行中的游戏")

    @filter.command("棋盘", alias={"board", "查看棋盘"})
    async def show_board(self, event: AstrMessageEvent):
        """查看当前棋盘"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        self._save_bot_client(event)

        # 检查井字棋
        ttt_game = self.ttt.get_game(group_id)
        if ttt_game and not ttt_game.is_finished:
            async for result in self._render_and_send(group_id, "ttt", ttt_game, event):
                yield result
            return

        # 检查围棋
        go_game = self.go.get_game(group_id)
        if go_game and not go_game.is_finished:
            async for result in self._render_and_send(group_id, "go", go_game, event):
                yield result
            return

        # 检查象棋
        xiangqi_game = self.xiangqi.get_game(group_id)
        if xiangqi_game and not xiangqi_game.is_finished:
            async for result in self._render_and_send(group_id, "xiangqi", xiangqi_game, event):
                yield result
            return

        # 检查五子棋
        gomoku_game = self.gomoku.get_game(group_id)
        if gomoku_game and not gomoku_game.is_finished:
            async for result in self._render_and_send(group_id, "gomoku", gomoku_game, event):
                yield result
            return

        # 检查军棋
        junqi_game = self.junqi.get_game(group_id)
        if junqi_game and not junqi_game.is_finished:
            async for result in self._render_junqi_game(junqi_game, event):
                yield result
            return

        yield event.plain_result("❌ 当前群没有进行中的游戏\n发送 /井字棋、/围棋、/象棋、/五子棋 或 /军棋 开始新游戏")

    @filter.command("结束游戏", alias={"endgame", "结束井字棋", "结束围棋", "结束象棋", "结束五子棋", "结束军棋"})
    async def end_game(self, event: AstrMessageEvent):
        """强制结束当前游戏"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        self._cancel_timeout(group_id)
        self._cancel_join_timeout(group_id)

        ended = False
        if self.ttt.end_game(group_id):
            ended = True
        if self.go.end_game(group_id):
            ended = True
        if self.xiangqi.end_game(group_id):
            ended = True
        if self.gomoku.end_game(group_id):
            ended = True
        if self.junqi.end_game(group_id):
            ended = True

        # 清理消息 ID
        self._last_msg_ids.pop(group_id, None)

        if ended:
            yield event.plain_result("✅ 游戏已结束")
        else:
            yield event.plain_result("❌ 当前群没有进行中的游戏")

    def _has_active_game(self, group_id: str) -> bool:
        """检查是否有进行中的游戏"""
        ttt = self.ttt.get_game(group_id)
        if ttt and not ttt.is_finished:
            return True
        go = self.go.get_game(group_id)
        if go and not go.is_finished:
            return True
        xq = self.xiangqi.get_game(group_id)
        if xq and not xq.is_finished:
            return True
        gmk = self.gomoku.get_game(group_id)
        if gmk and not gmk.is_finished:
            return True
        jq = self.junqi.get_game(group_id)
        if jq and not jq.is_finished:
            return True
        return False

    # ========== 围棋 ==========

    @filter.command("围棋", alias={"go", "weiqi"})
    async def go_start(self, event: AstrMessageEvent, size: str = "9"):
        """发起一局围棋。用法：/围棋 [9/13/19]"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 围棋仅支持群聊中使用")
            return

        try:
            board_size = int(size)
        except ValueError:
            yield event.plain_result("❌ 棋盘大小必须是数字（9、13 或 19）")
            return

        if board_size not in [9, 13, 19]:
            yield event.plain_result("❌ 棋盘大小只支持 9、13、19")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        # 检查是否有其他游戏进行中
        if self._has_active_game(group_id):
            yield event.plain_result("❌ 当前群有进行中的游戏\n发送 /结束游戏 可强制结束")
            return

        success, msg, game = self.go.create_game(group_id, player_id, board_size)

        if not success:
            yield event.plain_result(f"❌ {msg}\n发送 /结束游戏 可强制结束当前游戏")
            return

        async for result in self._render_and_send(group_id, "go", game, event):
            yield result

    @filter.command("加入围棋", alias={"joingo"})
    async def go_join(self, event: AstrMessageEvent):
        """加入一局围棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.go.join_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "go", game, event):
            yield result

    @filter.command("落子", alias={"play", "p"})
    async def go_move(self, event: AstrMessageEvent, coord: str = None):
        """围棋落子。用法：/落子 D4"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        if not coord:
            yield event.plain_result("❌ 请指定坐标，例如：/落子 D4")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.go.make_move(group_id, player_id, coord)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "go", game, event):
            yield result

    @filter.command("虚着", alias={"pass", "跳过"})
    async def go_pass(self, event: AstrMessageEvent):
        """围棋虚着（PASS）"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        self._save_bot_client(event)

        success, msg, game = self.go.pass_turn(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        if game.is_finished:
            self._cancel_timeout(group_id)
            score_b, score_w, details = game.count_territory()
            result_text = (
                f"🏁 双方连续虚着，游戏结束！\n"
                f"📊 计分结果（中国规则 · 贴{game.komi}目）：\n"
                f"⚫ 黑方: 棋子{details['black_stones']} + 地盘{details['black_territory']} = {score_b}\n"
                f"⚪ 白方: 棋子{details['white_stones']} + 地盘{details['white_territory']} + 贴目{game.komi} = {score_w}"
            )
            yield event.plain_result(result_text)

        async for result in self._render_and_send(group_id, "go", game, event):
            yield result

    @filter.command("点目", alias={"score", "形势"})
    async def go_score(self, event: AstrMessageEvent):
        """围棋点目（查看当前形势判断）"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)

        game = self.go.get_game(group_id)
        if not game:
            yield event.plain_result("❌ 当前群没有进行中的围棋游戏")
            return

        score_b, score_w, details = game.count_territory()
        diff = abs(score_b - score_w)
        leading = "黑方" if score_b > score_w else "白方"

        text = (
            f"📊 当前形势（中国规则 · 贴{game.komi}目）\n"
            f"━" * 20 + "\n"
            f"⚫ 黑方: 棋子{details['black_stones']} + 地盘{details['black_territory']} = {score_b}\n"
            f"⚪ 白方: 棋子{details['white_stones']} + 地盘{details['white_territory']} + 贴目{game.komi} = {score_w}\n"
            f"━" * 20 + "\n"
            f"👉 {leading}领先 {diff} 目\n"
            f"\n"
            f"⚠️ 仅供参考，未扣除死子"
        )
        yield event.plain_result(text)

    @filter.command("悔棋", alias={"undo", "撤回"})
    async def go_undo(self, event: AstrMessageEvent):
        """围棋悔棋（撤回上一步）"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        self._save_bot_client(event)

        success, msg, game = self.go.undo(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        yield event.plain_result("✅ 悔棋成功")
        async for result in self._render_and_send(group_id, "go", game, event):
            yield result

    @filter.command("请求计分", alias={"requestscore", "申请计分", "同意计分"})
    async def go_request_score(self, event: AstrMessageEvent):
        """围棋请求计分（需双方同意）"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        self._save_bot_client(event)

        success, msg, game = self.go.request_score(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        if msg == "request_pending":
            # 首个请求
            player_name = self._player_names.get(player_id, player_id[:8])
            yield event.plain_result(
                f"📋 {player_name} 请求计分结束游戏\n"
                f"对方发送 /同意计分 同意，或 /拒绝计分 拒绝"
            )
        elif msg == "agreed":
            # 双方同意，游戏结束
            self._cancel_timeout(group_id)
            score_b, score_w, details = game.count_territory()
            result_text = (
                f"🏁 双方同意计分，游戏结束！\n"
                f"📊 计分结果（中国规则 · 贴{game.komi}目）：\n"
                f"⚫ 黑方: 棋子{details['black_stones']} + 地盘{details['black_territory']} = {score_b}\n"
                f"⚪ 白方: 棋子{details['white_stones']} + 地盘{details['white_territory']} + 贴目{game.komi} = {score_w}"
            )
            yield event.plain_result(result_text)
            async for result in self._render_and_send(group_id, "go", game, event):
                yield result

    @filter.command("拒绝计分", alias={"rejectscore", "继续游戏"})
    async def go_reject_score(self, event: AstrMessageEvent):
        """围棋拒绝计分请求"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())

        success, msg, game = self.go.reject_score(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        yield event.plain_result(f"✅ {msg}")

    # ========== 象棋 ==========

    @filter.command("象棋", alias={"xiangqi", "中国象棋"})
    async def xiangqi_start(self, event: AstrMessageEvent):
        """发起一局象棋。用法：/象棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 象棋仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        # 检查是否有其他游戏进行中
        if self._has_active_game(group_id):
            yield event.plain_result("❌ 当前群有进行中的游戏\n发送 /结束游戏 可强制结束")
            return

        success, msg, game = self.xiangqi.create_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}\n发送 /结束游戏 可强制结束当前游戏")
            return

        async for result in self._render_and_send(group_id, "xiangqi", game, event):
            yield result

    @filter.command("加入象棋", alias={"joinxiangqi"})
    async def xiangqi_join(self, event: AstrMessageEvent):
        """加入一局象棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.xiangqi.join_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "xiangqi", game, event):
            yield result

    @filter.command("走棋", alias={"xmove", "xm"})
    async def xiangqi_move(self, event: AstrMessageEvent, move: str = None):
        """象棋走棋。用法：/走棋 E1-E2"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        if not move:
            yield event.plain_result("❌ 请指定走法，例如：/走棋 E1-E2 或 /走棋 5,1-5,2")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.xiangqi.make_move(group_id, player_id, move)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "xiangqi", game, event):
            yield result

    # ========== 帮助 ==========

    @filter.command("游戏帮助", alias={"gamehelp", "游戏", "小游戏"})
    async def game_help(self, event: AstrMessageEvent):
        """查看小游戏合集帮助"""
        # 尝试渲染图片
        img_path = await self.renderer.render_game_help(subtitle="Game Plugin v1.0")

        if img_path:
            yield event.image_result(img_path)
        else:
            # 渲染失败时返回文本
            help_text = (
                "🎮 小游戏合集\n"
                "━" * 20 + "\n"
                "\n"
                "🔴 井字棋: /井字棋 · /下棋 <1-9>\n"
                "⚫ 围棋: /围棋 · /落子 <坐标> · /虚着\n"
                "🀄 象棋: /象棋 · /走棋 <起点>-<终点>\n"
                "⬛ 五子棋: /五子棋 · /五子 <坐标>\n"
                "🎖️ 军棋: /军棋 · /翻 <坐标> · /军 <起点>-<终点>\n"
                "\n"
                "通用: /棋盘 · /认输 · /结束游戏"
            )
            yield event.plain_result(help_text)

    # ========== 五子棋 ==========

    @filter.command("五子棋", alias={"gomoku", "wuziqi"})
    async def gomoku_start(self, event: AstrMessageEvent, size: str = "15"):
        """发起一局五子棋。用法：/五子棋 [13/15/19]"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 五子棋仅支持群聊中使用")
            return

        try:
            board_size = int(size)
        except ValueError:
            yield event.plain_result("❌ 棋盘大小必须是数字（13、15 或 19）")
            return

        if board_size not in [13, 15, 19]:
            yield event.plain_result("❌ 棋盘大小只支持 13、15、19")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        # 检查是否有其他游戏进行中
        if self._has_active_game(group_id):
            yield event.plain_result("❌ 当前群有进行中的游戏\n发送 /结束游戏 可强制结束")
            return

        success, msg, game = self.gomoku.create_game(group_id, player_id, board_size)

        if not success:
            yield event.plain_result(f"❌ {msg}\n发送 /结束游戏 可强制结束当前游戏")
            return

        async for result in self._render_and_send(group_id, "gomoku", game, event):
            yield result

    @filter.command("加入五子棋", alias={"joingomoku"})
    async def gomoku_join(self, event: AstrMessageEvent):
        """加入一局五子棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.gomoku.join_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "gomoku", game, event):
            yield result

    @filter.command("五子", alias={"gmove", "gm"})
    async def gomoku_move(self, event: AstrMessageEvent, coord: str = None):
        """五子棋落子。用法：/五子 H8"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        if not coord:
            yield event.plain_result("❌ 请指定坐标，例如：/五子 H8 或 /五子 8,8")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.gomoku.make_move(group_id, player_id, coord)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_and_send(group_id, "gomoku", game, event):
            yield result

    # ========== 军棋 ==========

    async def _render_junqi_game(self, game, event: AstrMessageEvent):
        """渲染军棋游戏状态并返回图片或文本"""
        a_name = self._player_names.get(game.player_a, game.player_a[:8])
        b_name = self._player_names.get(game.player_b, game.player_b[:8] if game.player_b else "")

        # 获取玩家阵营
        a_side = game.player_a_side.name if game.player_a_side else None
        b_side = None
        if game.player_a_side:
            b_side = "BLUE" if game.player_a_side.name == "RED" else "RED"

        board_data = game.get_board_for_render()
        subtitle = f"第 {game.move_count} 步" if game.move_count > 0 else "游戏开始"

        img_path = await self.renderer.render_junqi(
            board=board_data,
            player_a_name=a_name,
            player_b_name=b_name,
            player_a_side=a_side,
            player_b_side=b_side,
            current_turn=game.current_turn,
            move_count=game.move_count,
            last_action=game.last_action,
            last_pos=game.last_pos,
            is_finished=game.is_finished,
            winner=self._player_names.get(game.winner, game.winner[:8]) if game.winner else None,
            subtitle=subtitle
        )

        if img_path:
            yield event.image_result(img_path)
        else:
            # 降级到文本
            yield event.plain_result("军棋游戏进行中（图片渲染失败）")

    @filter.command("军棋", alias={"junqi", "翻棋"})
    async def junqi_start(self, event: AstrMessageEvent):
        """发起一局军棋翻棋。用法：/军棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 军棋仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        if self._has_active_game(group_id):
            yield event.plain_result("❌ 当前群有进行中的游戏\n发送 /结束游戏 可强制结束")
            return

        success, msg, game = self.junqi.create_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_junqi_game(game, event):
            yield result

    @filter.command("加入军棋", alias={"joinjunqi"})
    async def junqi_join(self, event: AstrMessageEvent):
        """加入一局军棋"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        player_name = event.get_sender_name()
        self._player_names[player_id] = player_name
        self._save_bot_client(event)

        success, msg, game = self.junqi.join_game(group_id, player_id)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_junqi_game(game, event):
            yield result

    @filter.command("翻", alias={"flip", "f"})
    async def junqi_flip(self, event: AstrMessageEvent, coord: str = None):
        """军棋翻棋。用法：/翻 A1"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        if not coord:
            yield event.plain_result("❌ 请指定坐标，例如：/翻 A1")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        self._save_bot_client(event)

        success, msg, game = self.junqi.flip(group_id, player_id, coord)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        async for result in self._render_junqi_game(game, event):
            yield result

    @filter.command("军", alias={"jmove", "jm"})
    async def junqi_move(self, event: AstrMessageEvent, move: str = None):
        """军棋移动/吃子。用法：/军 A1-A2"""
        group_id = event.get_group_id()
        if not group_id:
            yield event.plain_result("❌ 仅支持群聊中使用")
            return

        if not move:
            yield event.plain_result("❌ 请指定移动，例如：/军 A1-A2")
            return

        group_id = str(group_id)
        player_id = str(event.get_sender_id())
        self._save_bot_client(event)

        success, msg, game = self.junqi.move(group_id, player_id, move)

        if not success:
            yield event.plain_result(f"❌ {msg}")
            return

        if game.is_finished and game.winner:
            winner_name = self._player_names.get(game.winner, game.winner[:8])
            yield event.plain_result(f"🏆 游戏结束！{winner_name} 获胜！")

        async for result in self._render_junqi_game(game, event):
            yield result

    async def terminate(self):
        """插件卸载"""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
        logger.info("小游戏插件已卸载")
