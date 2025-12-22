import json
import random
import socket
import threading
import time
from datetime import datetime

# 游戏服务器配置
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8888
MAX_PLAYERS = 4
GAME_DURATION = 60  # 游戏时长60秒


# 游戏状态
class GameServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.players = {}
        self.player_id_counter = 1
        self.game_state = {
            'players': {},
            'small_fish': [],
            'game_started': False,
            'game_start_time': None,
            'game_duration': GAME_DURATION
        }
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        """启动服务器"""
        try:
            self.server.bind((SERVER_HOST, SERVER_PORT))
            self.server.listen(MAX_PLAYERS)
            print(f"游戏服务器已启动，监听 {SERVER_HOST}:{SERVER_PORT}")
            print(f"最多支持 {MAX_PLAYERS} 名玩家同时游戏")

            # 启动游戏状态更新线程
            update_thread = threading.Thread(target=self.update_game_state, daemon=True)
            update_thread.start()

            # 接受客户端连接
            while self.running:
                client, address = self.server.accept()
                print(f"新的连接: {address}")
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client, address)
                )
                client_handler.start()

        except Exception as e:
            print(f"服务器启动失败: {e}")
        finally:
            self.server.close()

    def handle_client(self, client, address):
        """处理客户端连接"""
        player_id = None
        try:
            # 接收玩家信息
            data = client.recv(1024).decode('utf-8')
            if data:
                player_info = json.loads(data)
                player_name = player_info.get('name', f'玩家{self.player_id_counter}')

                with self.lock:
                    player_id = self.player_id_counter
                    self.player_id_counter += 1

                    # 创建新玩家
                    self.players[player_id] = {
                        'socket': client,
                        'address': address,
                        'name': player_name,
                        'score': 0,
                        'position': {
                            'x': random.randint(100, 700),
                            'y': random.randint(100, 500)
                        },
                        'size': 80,  # 大鱼尺寸
                        'color': self.generate_random_color(),
                        'last_update': time.time(),
                        'active': True
                    }

                    # 发送欢迎消息和玩家ID
                    welcome_msg = {
                        'type': 'welcome',
                        'player_id': player_id,
                        'message': f'欢迎 {player_name} 加入游戏!',
                        'max_players': MAX_PLAYERS
                    }
                    client.send(json.dumps(welcome_msg).encode('utf-8'))

                    print(f"玩家 {player_name} (ID: {player_id}) 已加入游戏")

                # 持续接收客户端数据
                while self.running:
                    try:
                        data = client.recv(1024).decode('utf-8')
                        if not data:
                            break

                        message = json.loads(data)
                        self.process_client_message(player_id, message)

                    except json.JSONDecodeError:
                        print(f"无效的JSON数据来自玩家 {player_id}")
                        break
                    except ConnectionResetError:
                        break

        except Exception as e:
            print(f"处理客户端 {address} 时出错: {e}")
        finally:
            # 客户端断开连接
            if player_id and player_id in self.players:
                with self.lock:
                    player_name = self.players[player_id]['name']
                    self.players[player_id]['active'] = False
                    print(f"玩家 {player_name} (ID: {player_id}) 断开连接")

                    # 广播玩家离开消息
                    leave_msg = {
                        'type': 'player_left',
                        'player_id': player_id,
                        'message': f'{player_name} 离开了游戏'
                    }
                    self.broadcast_message(leave_msg, exclude_id=player_id)

                    # 移除玩家
                    del self.players[player_id]

            client.close()

    def process_client_message(self, player_id, message):
        """处理客户端消息"""
        msg_type = message.get('type')

        with self.lock:
            if player_id not in self.players:
                return

            player = self.players[player_id]
            player['last_update'] = time.time()

            if msg_type == 'movement':
                # 更新玩家位置
                new_x = message.get('x', player['position']['x'])
                new_y = message.get('y', player['position']['y'])

                # 边界检查
                new_x = max(0, min(new_x, 800 - player['size']))
                new_y = max(100, min(new_y, 700 - player['size'] / 2))

                player['position']['x'] = new_x
                player['position']['y'] = new_y

            elif msg_type == 'eat_fish':
                # 玩家吃小鱼
                fish_id = message.get('fish_id')
                if fish_id in self.game_state['small_fish']:
                    self.game_state['small_fish'].remove(fish_id)
                    player['score'] += 10

                    # 发送得分更新
                    score_msg = {
                        'type': 'score_update',
                        'player_id': player_id,
                        'score': player['score']
                    }
                    self.send_to_player(player_id, score_msg)

            elif msg_type == 'chat':
                # 聊天消息
                chat_msg = {
                    'type': 'chat',
                    'player_id': player_id,
                    'player_name': player['name'],
                    'message': message.get('message', ''),
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                }
                self.broadcast_message(chat_msg)

            elif msg_type == 'ready':
                # 玩家准备状态
                if len(self.players) >= 2 and not self.game_state['game_started']:
                    self.start_game()

    def generate_random_color(self):
        """生成随机颜色"""
        return {
            'r': random.randint(0, 255),
            'g': random.randint(0, 255),
            'b': random.randint(0, 255)
        }

    def start_game(self):
        """开始游戏"""
        self.game_state['game_started'] = True
        self.game_state['game_start_time'] = time.time()

        # 初始化小鱼
        self.game_state['small_fish'] = list(range(15))

        # 广播游戏开始
        start_msg = {
            'type': 'game_start',
            'message': '游戏开始!',
            'duration': GAME_DURATION
        }
        self.broadcast_message(start_msg)
        print("游戏开始!")

    def update_game_state(self):
        """定期更新游戏状态"""
        while self.running:
            try:
                with self.lock:
                    current_time = time.time()

                    # 检查游戏是否超时
                    if self.game_state['game_started']:
                        elapsed = current_time - self.game_state['game_start_time']
                        if elapsed >= GAME_DURATION:
                            self.end_game()

                    # 定期生成小鱼
                    if len(self.game_state['small_fish']) < 15:
                        self.game_state['small_fish'].append(len(self.game_state['small_fish']))

                    # 准备游戏状态数据
                    game_state = {
                        'type': 'game_state',
                        'players': {},
                        'small_fish': self.game_state['small_fish'],
                        'time_left': max(0, GAME_DURATION - (current_time - self.game_state['game_start_time']))
                        if self.game_state['game_started'] else GAME_DURATION
                    }

                    # 添加玩家数据
                    for pid, player in self.players.items():
                        if player['active']:
                            game_state['players'][pid] = {
                                'name': player['name'],
                                'score': player['score'],
                                'position': player['position'],
                                'size': player['size'],
                                'color': player['color']
                            }

                    # 广播游戏状态
                    self.broadcast_message(game_state)

                time.sleep(0.05)  # 20次/秒更新频率

            except Exception as e:
                print(f"更新游戏状态时出错: {e}")

    def end_game(self):
        """结束游戏"""
        self.game_state['game_started'] = False

        # 计算获胜者
        scores = [(pid, player['name'], player['score'])
                  for pid, player in self.players.items() if player['active']]
        scores.sort(key=lambda x: x[2], reverse=True)

        winner_msg = {
            'type': 'game_over',
            'winner': scores[0][1] if scores else None,
            'scores': [{'name': name, 'score': score} for _, name, score in scores]
        }

        self.broadcast_message(winner_msg)
        print("游戏结束!")

        # 重置玩家分数
        for player in self.players.values():
            player['score'] = 0

    def broadcast_message(self, message, exclude_id=None):
        """广播消息给所有玩家"""
        data = json.dumps(message).encode('utf-8')

        for pid, player in list(self.players.items()):
            if pid != exclude_id and player['active']:
                try:
                    player['socket'].send(data)
                except:
                    player['active'] = False

    def send_to_player(self, player_id, message):
        """发送消息给指定玩家"""
        if player_id in self.players and self.players[player_id]['active']:
            try:
                data = json.dumps(message).encode('utf-8')
                self.players[player_id]['socket'].send(data)
            except:
                self.players[player_id]['active'] = False

    def stop(self):
        """停止服务器"""
        self.running = False
        self.server.close()


if __name__ == "__main__":
    print("=== 海底世界多人游戏服务器 ===")
    server = GameServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
        server.stop()