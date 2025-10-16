import pygame
import random
import time
import json
import os
from datetime import datetime
from enum import Enum
import socketio
import requests
from threading import Thread

# Initialize Pygame
pygame.init()

# Colors - Modern Dark Theme
BG_COLOR = (40, 44, 52)
PANEL_BG = (33, 37, 41)
BUTTON_COLOR = (52, 152, 219)
BUTTON_HOVER = (41, 128, 185)
BUTTON_DISABLED = (108, 117, 125)
CELL_HIDDEN = (149, 165, 166)
CELL_REVEALED = (236, 240, 241)
CELL_HOVER = (189, 195, 199)
TEXT_COLOR = (236, 240, 241)
MINE_COLOR = (231, 76, 60)
FLAG_COLOR = (46, 204, 113)
HINT_COLOR = (241, 196, 15)
CHEAT_COLOR = (255, 0, 255)  # Magenta for cheat mode
PLAYER_COLORS = [(255, 215, 0), (138, 43, 226), (0, 255, 127), (255, 105, 180)]  # Gold, Purple, Spring Green, Hot Pink

# Number colors
NUMBER_COLORS = {
    1: (52, 152, 219),  # Blue
    2: (46, 204, 113),  # Green
    3: (231, 76, 60),   # Red
    4: (155, 89, 182),  # Purple
    5: (230, 126, 34),  # Orange
    6: (26, 188, 156),  # Turquoise
    7: (52, 73, 94),    # Dark gray
    8: (44, 62, 80)     # Darker gray
}

# Server configuration - Railway deployment
SERVER_URL = os.environ.get('SERVER_URL', 'https://minesweeper-server-production-ecec.up.railway.app')

class Difficulty(Enum):
    EASY = ("Easy", 9, 9, 10)
    MEDIUM = ("Medium", 16, 16, 40)
    HARD = ("Hard", 16, 30, 99)

    def __init__(self, name, rows, cols, mines):
        self.display_name = name
        self.rows = rows
        self.cols = cols
        self.mines = mines

class Cell:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.is_mine = False
        self.is_revealed = False
        self.is_flagged = False
        self.adjacent_mines = 0

class Button:
    def __init__(self, x, y, width, height, text, callback=None, font_size=20):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.enabled = True
        self.font = pygame.font.Font(None, font_size)

    def draw(self, screen):
        if self.enabled:
            color = BUTTON_HOVER if self.hovered else BUTTON_COLOR
        else:
            color = BUTTON_DISABLED

        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        pygame.draw.rect(screen, TEXT_COLOR, self.rect, 2, border_radius=5)

        text_surface = self.font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.callback:
                self.callback()
                return True
        return False

def get_username():
    """Get username via a simple pygame input box"""
    screen = pygame.display.set_mode((500, 200))
    pygame.display.set_caption('Enter Username')

    font = pygame.font.Font(None, 32)
    input_box = pygame.Rect(50, 100, 400, 40)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = False
    text = ''
    done = False

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        done = True
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    else:
                        if len(text) < 20:
                            text += event.unicode

        screen.fill(BG_COLOR)

        # Title
        title = font.render('Enter Your Username:', True, TEXT_COLOR)
        title_rect = title.get_rect(center=(250, 40))
        screen.blit(title, title_rect)

        # Input box
        txt_surface = font.render(text, True, color)
        width = max(400, txt_surface.get_width()+10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x+5, input_box.y+5))
        pygame.draw.rect(screen, color, input_box, 2, border_radius=5)

        # Instructions
        inst_font = pygame.font.Font(None, 20)
        inst = inst_font.render('Press ENTER when done', True, TEXT_COLOR)
        inst_rect = inst.get_rect(center=(250, 160))
        screen.blit(inst, inst_rect)

        pygame.display.flip()

    return text if text else "Player"

def choose_game_mode():
    """Choose between solo and multiplayer"""
    screen = pygame.display.set_mode((600, 350))
    pygame.display.set_caption('Choose Game Mode')

    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 32)

    solo_btn = Button(150, 150, 120, 50, "Solo", font_size=32)
    multi_btn = Button(330, 150, 120, 50, "Multiplayer", font_size=24)
    back_btn = Button(200, 240, 200, 50, "Back", font_size=28)

    choice = None
    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            # Update button hover states
            if event.type == pygame.MOUSEMOTION:
                solo_btn.hovered = solo_btn.rect.collidepoint(event.pos)
                multi_btn.hovered = multi_btn.rect.collidepoint(event.pos)
                back_btn.hovered = back_btn.rect.collidepoint(event.pos)

            # Check for button clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if solo_btn.rect.collidepoint(event.pos):
                    choice = "solo"
                    running = False
                elif multi_btn.rect.collidepoint(event.pos):
                    choice = "multiplayer"
                    running = False
                elif back_btn.rect.collidepoint(event.pos):
                    choice = "back"
                    running = False

        screen.fill(BG_COLOR)

        # Title
        title = font_large.render('Choose Game Mode', True, TEXT_COLOR)
        title_rect = title.get_rect(center=(300, 60))
        screen.blit(title, title_rect)

        # Draw buttons
        solo_btn.draw(screen)
        multi_btn.draw(screen)
        back_btn.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    return choice

def multiplayer_lobby():
    """Create or join a room"""
    screen = pygame.display.set_mode((600, 400))
    pygame.display.set_caption('Multiplayer Lobby')

    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 24)

    create_btn = Button(200, 150, 200, 50, "Create Room", font_size=28)
    join_btn = Button(200, 220, 200, 50, "Join Room", font_size=28)
    back_btn = Button(200, 290, 200, 50, "Back", font_size=28)

    choice = None
    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            # Update button hover states
            if event.type == pygame.MOUSEMOTION:
                create_btn.hovered = create_btn.rect.collidepoint(event.pos)
                join_btn.hovered = join_btn.rect.collidepoint(event.pos)
                back_btn.hovered = back_btn.rect.collidepoint(event.pos)

            # Check for button clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if create_btn.rect.collidepoint(event.pos):
                    choice = "create"
                    running = False
                elif join_btn.rect.collidepoint(event.pos):
                    choice = "join"
                    running = False
                elif back_btn.rect.collidepoint(event.pos):
                    choice = "back"
                    running = False

        screen.fill(BG_COLOR)

        # Title
        title = font_large.render('Multiplayer Lobby', True, TEXT_COLOR)
        title_rect = title.get_rect(center=(300, 60))
        screen.blit(title, title_rect)

        # Draw buttons
        create_btn.draw(screen)
        join_btn.draw(screen)
        back_btn.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    return choice

def get_room_code():
    """Get room code from user"""
    screen = pygame.display.set_mode((500, 200))
    pygame.display.set_caption('Enter Room Code')

    font = pygame.font.Font(None, 48)
    input_box = pygame.Rect(150, 100, 200, 50)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = False
    text = ''
    done = False

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        done = True
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    else:
                        if len(text) < 6 and event.unicode.isalnum():
                            text += event.unicode.upper()

        screen.fill(BG_COLOR)

        # Title
        title_font = pygame.font.Font(None, 32)
        title = title_font.render('Enter Room Code:', True, TEXT_COLOR)
        title_rect = title.get_rect(center=(250, 40))
        screen.blit(title, title_rect)

        # Input box
        txt_surface = font.render(text, True, color)
        width = max(200, txt_surface.get_width()+10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x+5, input_box.y+5))
        pygame.draw.rect(screen, color, input_box, 2, border_radius=5)

        # Instructions
        inst_font = pygame.font.Font(None, 20)
        inst = inst_font.render('Press ENTER when done', True, TEXT_COLOR)
        inst_rect = inst.get_rect(center=(250, 160))
        screen.blit(inst, inst_rect)

        pygame.display.flip()

    return text if text else None

def choose_multiplayer_game_mode():
    """Choose between Luck Mode and Standard Mode for multiplayer"""
    screen = pygame.display.set_mode((700, 500))
    pygame.display.set_caption('Choose Multiplayer Mode')

    font_large = pygame.font.Font(None, 48)
    font_medium = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)

    luck_btn = Button(150, 200, 180, 60, "Luck Mode", font_size=28)
    standard_btn = Button(370, 200, 180, 60, "Standard Mode", font_size=24)
    back_btn = Button(250, 420, 200, 50, "Back", font_size=28)

    choice = None
    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            # Update button hover states
            if event.type == pygame.MOUSEMOTION:
                luck_btn.hovered = luck_btn.rect.collidepoint(event.pos)
                standard_btn.hovered = standard_btn.rect.collidepoint(event.pos)
                back_btn.hovered = back_btn.rect.collidepoint(event.pos)

            # Check for button clicks
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if luck_btn.rect.collidepoint(event.pos):
                    choice = "luck"
                    running = False
                elif standard_btn.rect.collidepoint(event.pos):
                    choice = "standard"
                    running = False
                elif back_btn.rect.collidepoint(event.pos):
                    choice = "back"
                    running = False

        screen.fill(BG_COLOR)

        # Title
        title = font_large.render('Choose Game Mode', True, TEXT_COLOR)
        title_rect = title.get_rect(center=(350, 50))
        screen.blit(title, title_rect)

        # Draw buttons
        luck_btn.draw(screen)
        standard_btn.draw(screen)
        back_btn.draw(screen)

        # Descriptions
        luck_desc1 = font_small.render("Turn-based: One click per turn", True, TEXT_COLOR)
        luck_desc2 = font_small.render("No numbers shown - pure luck!", True, TEXT_COLOR)
        screen.blit(luck_desc1, (150, 270))
        screen.blit(luck_desc2, (150, 290))

        standard_desc1 = font_small.render("Race Mode: Normal minesweeper", True, TEXT_COLOR)
        standard_desc2 = font_small.render("First to finish wins!", True, TEXT_COLOR)
        screen.blit(standard_desc1, (370, 270))
        screen.blit(standard_desc2, (370, 290))

        pygame.display.flip()
        clock.tick(60)

    return choice

class NetworkManager:
    def __init__(self):
        self.sio = socketio.Client()
        self.connected = False
        self.room_code = None
        self.players = []
        self.game_started = False
        self.board_seed = None
        self.game_mode = "standard"  # "standard" or "luck"
        self.current_turn = None  # For Luck Mode: username of player whose turn it is
        self.game_result = None  # "won", "lost", or None

        # Setup event handlers
        self.setup_handlers()

    def setup_handlers(self):
        @self.sio.on('connected')
        def on_connected(data):
            print(f"Connected to server: {data}")
            self.connected = True

        @self.sio.on('room_created')
        def on_room_created(data):
            self.room_code = data['room_code']
            print(f"Room created: {self.room_code}")

        @self.sio.on('room_joined')
        def on_room_joined(data):
            self.room_code = data['room_code']
            self.players = data['players']
            print(f"Joined room: {self.room_code}")

        @self.sio.on('player_joined')
        def on_player_joined(data):
            self.players = data['players']
            print(f"Player joined: {data['username']}")

        @self.sio.on('player_left')
        def on_player_left(data):
            print(f"Player left: {data['username']}")

        @self.sio.on('player_ready_update')
        def on_ready_update(data):
            self.players = data['players']

        @self.sio.on('game_start')
        def on_game_start(data):
            self.game_started = True
            self.board_seed = data['board_seed']
            self.game_mode = data.get('game_mode', 'standard')
            self.current_turn = data.get('current_turn')
            print(f"Game starting! Mode: {self.game_mode}")

        @self.sio.on('player_action')
        def on_player_action(data):
            print(f"Player {data['username']} performed action: {data['action']}")

        @self.sio.on('player_finished')
        def on_player_finished(data):
            self.players = data['players']
            print(f"Player {data['username']} finished! Score: {data['score']}")

        @self.sio.on('game_ended')
        def on_game_ended(data):
            print("Game ended! Results:", data['results'])
            # Set game result based on position
            results = data['results']
            my_username = [p['username'] for p in self.players if p['session_id'] == self.sio.sid]
            if my_username:
                my_username = my_username[0]
                if results[0]['username'] == my_username:
                    self.game_result = "won"
                else:
                    self.game_result = "lost"

        @self.sio.on('turn_changed')
        def on_turn_changed(data):
            """Handle turn change in Luck Mode"""
            self.current_turn = data['current_turn']
            print(f"Turn changed to: {self.current_turn}")

        @self.sio.on('player_eliminated')
        def on_player_eliminated(data):
            """Handle player elimination in Luck Mode"""
            print(f"Player {data['username']} was eliminated!")
            if data.get('winner'):
                self.game_result = "won" if data['winner'] == player_sessions.get(self.sio.sid, {}).get('username') else "lost"

        @self.sio.on('error')
        def on_error(data):
            print(f"Error: {data['message']}")

    def connect(self):
        try:
            self.sio.connect(SERVER_URL)
            time.sleep(0.5)  # Wait for connection
            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False

    def disconnect(self):
        if self.connected:
            self.sio.disconnect()

    def create_room(self, username, difficulty="Medium", game_mode="standard"):
        self.sio.emit('create_room', {
            "username": username,
            "difficulty": difficulty,
            "max_players": 3,
            "game_mode": game_mode
        })
        self.game_mode = game_mode
        time.sleep(0.5)  # Wait for response

    def join_room(self, room_code, username):
        self.sio.emit('join_room', {
            "room_code": room_code,
            "username": username
        })
        time.sleep(0.5)  # Wait for response

    def mark_ready(self):
        self.sio.emit('player_ready', {})

    def send_action(self, action, row, col):
        self.sio.emit('game_action', {
            "action": action,
            "row": row,
            "col": col
        })

    def send_finished(self, score, time_taken):
        self.sio.emit('game_finished', {
            "score": score,
            "time": time_taken
        })

class MinesweeperGame:
    def __init__(self, username, mode="solo", network_manager=None):
        self.username = username
        self.mode = mode
        self.network = network_manager
        # Block "Player 1" from being the cheat username - only "ICantLose" works
        self.cheat_mode = (username == "ICantLose")
        self.difficulty = Difficulty.MEDIUM
        self.cell_size = 30
        self.top_panel_height = 180  # Increased for multiplayer info
        self.right_panel_width = 250
        self.padding = 20
        self.game_mode = "standard"  # "standard" or "luck"
        self.show_game_result = False  # Show win/loss screen overlay

        self.setup_window()
        self.load_leaderboard()
        self.reset_game()
        self.create_ui_elements()

        if self.cheat_mode:
            print(f"\n🎮 CHEAT MODE ACTIVATED! {self.username} can see all mines! 🎮\n")

    def get_display_username(self):
        """Get username for sending to server/leaderboard - masks cheat username"""
        if self.cheat_mode:
            return "Player 1"
        return self.username

    def setup_window(self):
        game_width = self.difficulty.cols * self.cell_size
        game_height = self.difficulty.rows * self.cell_size

        self.width = game_width + self.right_panel_width + self.padding * 3
        self.height = game_height + self.top_panel_height + self.padding * 2

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(f'Minesweeper - {self.username}')

        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 18)

    def create_ui_elements(self):
        # Mode buttons
        button_width = 80
        button_y = self.padding + 50
        spacing = 10

        self.easy_btn = Button(self.padding, button_y, button_width, 35, "Easy",
                               lambda: self.change_difficulty(Difficulty.EASY))
        self.medium_btn = Button(self.padding + button_width + spacing, button_y, button_width, 35, "Medium",
                                 lambda: self.change_difficulty(Difficulty.MEDIUM))
        self.hard_btn = Button(self.padding + 2 * (button_width + spacing), button_y, button_width, 35, "Hard",
                               lambda: self.change_difficulty(Difficulty.HARD))

        # Control buttons - adjust positioning based on cheat mode and difficulty
        game_width = self.difficulty.cols * self.cell_size

        if self.cheat_mode:
            new_x = self.padding + game_width - 90
            hint_x = new_x - 90
            clear_x = hint_x - 110

            min_clear_x = self.padding + 3 * (button_width + spacing) + spacing
            if clear_x < min_clear_x:
                clear_x = min_clear_x
                hint_x = clear_x + 110
                new_x = hint_x + 90

            self.clear_btn = Button(clear_x, button_y, 100, 35, "Clear Board", self.auto_win)
            self.hint_btn = Button(hint_x, button_y, 80, 35, "Hint (H)", self.use_hint)
            self.new_game_btn = Button(new_x, button_y, 80, 35, "New (F2)", self.reset_game)
            self.buttons = [self.easy_btn, self.medium_btn, self.hard_btn, self.clear_btn, self.hint_btn, self.new_game_btn]
        else:
            new_x = self.padding + game_width - 90
            hint_x = new_x - 90

            min_hint_x = self.padding + 3 * (button_width + spacing) + spacing
            if hint_x < min_hint_x:
                hint_x = min_hint_x
                new_x = hint_x + 90

            self.hint_btn = Button(hint_x, button_y, 80, 35, "Hint (H)", self.use_hint)
            self.new_game_btn = Button(new_x, button_y, 80, 35, "New (F2)", self.reset_game)
            self.buttons = [self.easy_btn, self.medium_btn, self.hard_btn, self.hint_btn, self.new_game_btn]

        # Multiplayer ready button
        if self.mode == "multiplayer" and self.network:
            ready_x = self.padding
            ready_y = self.padding + 95
            self.ready_btn = Button(ready_x, ready_y, 150, 35, "Ready", self.mark_ready)
            self.buttons.append(self.ready_btn)

    def mark_ready(self):
        if self.network and not self.network.game_started:
            self.network.mark_ready()
            self.ready_btn.enabled = False
            self.ready_btn.text = "Waiting..."

    def change_difficulty(self, difficulty):
        # Disable difficulty change in multiplayer
        if self.mode == "multiplayer":
            return

        self.difficulty = difficulty
        self.setup_window()
        self.reset_game()
        self.create_ui_elements()

    def reset_game(self):
        # Use network seed if in multiplayer
        if self.mode == "multiplayer" and self.network and self.network.board_seed:
            random.seed(self.network.board_seed)

        self.board = [[Cell(row, col) for col in range(self.difficulty.cols)]
                      for row in range(self.difficulty.rows)]
        self.game_over = False
        self.game_won = False
        self.first_click = True
        self.start_time = None
        self.elapsed_time = 0
        self.flags_placed = 0
        self.hints_remaining = 3
        self.hint_cell = None
        self.hovered_cell = None
        self.score = 0

    def place_mines(self, exclude_row, exclude_col):
        mines_placed = 0
        exclude_cells = set()

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                r, c = exclude_row + dr, exclude_col + dc
                if 0 <= r < self.difficulty.rows and 0 <= c < self.difficulty.cols:
                    exclude_cells.add((r, c))

        while mines_placed < self.difficulty.mines:
            row = random.randint(0, self.difficulty.rows - 1)
            col = random.randint(0, self.difficulty.cols - 1)

            if not self.board[row][col].is_mine and (row, col) not in exclude_cells:
                self.board[row][col].is_mine = True
                mines_placed += 1

        # Calculate adjacent mines
        for row in range(self.difficulty.rows):
            for col in range(self.difficulty.cols):
                if not self.board[row][col].is_mine:
                    count = 0
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            r, c = row + dr, col + dc
                            if 0 <= r < self.difficulty.rows and 0 <= c < self.difficulty.cols:
                                if self.board[r][c].is_mine:
                                    count += 1
                    self.board[row][col].adjacent_mines = count

    def reveal_cell(self, row, col):
        if row < 0 or row >= self.difficulty.rows or col < 0 or col >= self.difficulty.cols:
            return

        cell = self.board[row][col]
        if cell.is_revealed or cell.is_flagged:
            return

        # In Luck Mode multiplayer, check if it's your turn
        if self.mode == "multiplayer" and self.network and self.game_mode == "luck":
            display_username = self.get_display_username()
            if self.network.current_turn and self.network.current_turn != display_username:
                return  # Not your turn

        # CHEAT MODE: Prevent clicking on mines
        if self.cheat_mode and cell.is_mine:
            return

        cell.is_revealed = True

        if self.first_click:
            self.first_click = False
            self.start_time = time.time()
            self.place_mines(row, col)
            cell = self.board[row][col]

        if cell.is_mine:
            self.game_over = True
            # In Luck Mode, you lose immediately
            if self.game_mode == "luck":
                if self.mode == "multiplayer" and self.network:
                    self.network.send_action("eliminated", row, col)
            else:
                self.reveal_all_mines()
            return

        # Send action to network if multiplayer
        if self.mode == "multiplayer" and self.network and self.network.game_started:
            self.network.send_action("reveal", row, col)

        # In Luck Mode, only reveal one cell (no flood fill)
        if self.game_mode == "luck":
            # Don't flood fill in Luck Mode
            pass
        else:
            # Standard mode: flood fill if no adjacent mines
            if cell.adjacent_mines == 0:
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        self.reveal_cell(row + dr, col + dc)

        self.check_win()

    def reveal_all_mines(self):
        for row in range(self.difficulty.rows):
            for col in range(self.difficulty.cols):
                if self.board[row][col].is_mine:
                    self.board[row][col].is_revealed = True

    def toggle_flag(self, row, col):
        if row < 0 or row >= self.difficulty.rows or col < 0 or col >= self.difficulty.cols:
            return

        cell = self.board[row][col]
        if cell.is_revealed:
            return

        cell.is_flagged = not cell.is_flagged
        if cell.is_flagged:
            self.flags_placed += 1
        else:
            self.flags_placed -= 1

        # Send action to network if multiplayer
        if self.mode == "multiplayer" and self.network and self.network.game_started:
            self.network.send_action("flag", row, col)

    def check_win(self):
        for row in range(self.difficulty.rows):
            for col in range(self.difficulty.cols):
                cell = self.board[row][col]
                if not cell.is_mine and not cell.is_revealed:
                    return

        self.game_won = True
        self.game_over = True
        self.calculate_score()

        # Send finished to network if multiplayer
        if self.mode == "multiplayer" and self.network and self.network.game_started:
            self.network.send_finished(self.score, self.elapsed_time)
        else:
            self.save_to_leaderboard()

    def calculate_score(self):
        if not self.game_won:
            self.score = 0
            return

        # Base score from difficulty
        difficulty_multiplier = {
            Difficulty.EASY: 1.0,
            Difficulty.MEDIUM: 2.0,
            Difficulty.HARD: 3.0
        }

        # Time bonus (faster = more points)
        time_score = max(0, 1000 - self.elapsed_time * 2)

        # Hint penalty (fewer hints used = more points)
        hint_bonus = self.hints_remaining * 100

        self.score = int((time_score + hint_bonus) * difficulty_multiplier[self.difficulty])

    def use_hint(self):
        if self.game_over or not self.start_time or self.hints_remaining <= 0:
            return

        # Find a safe cell
        safe_cells = []
        for row in range(self.difficulty.rows):
            for col in range(self.difficulty.cols):
                cell = self.board[row][col]
                if not cell.is_revealed and not cell.is_mine and not cell.is_flagged:
                    safe_cells.append((row, col))

        if safe_cells:
            self.hint_cell = random.choice(safe_cells)
            self.hints_remaining -= 1

    def auto_win(self):
        """Cheat mode: Reveal all non-mine cells instantly"""
        if not self.cheat_mode:
            return

        # Start timer if not started
        if not self.start_time:
            self.start_time = time.time()

        # Reveal all non-mine cells
        for row in range(self.difficulty.rows):
            for col in range(self.difficulty.cols):
                cell = self.board[row][col]
                if not cell.is_mine:
                    cell.is_revealed = True

        # Trigger win
        self.check_win()

    def get_cell_from_pos(self, pos):
        x, y = pos
        x -= self.padding
        y -= self.top_panel_height

        if x < 0 or y < 0:
            return None, None

        col = x // self.cell_size
        row = y // self.cell_size

        if row >= self.difficulty.rows or col >= self.difficulty.cols:
            return None, None

        return row, col

    def load_leaderboard(self):
        self.leaderboard_file = os.path.join(os.path.dirname(__file__), 'leaderboard.json')
        try:
            if os.path.exists(self.leaderboard_file):
                with open(self.leaderboard_file, 'r') as f:
                    data = json.load(f)
                    self.leaderboard = {
                        "Easy": data.get("Easy", []),
                        "Medium": data.get("Medium", []),
                        "Hard": data.get("Hard", [])
                    }
            else:
                self.leaderboard = {
                    "Easy": [],
                    "Medium": [],
                    "Hard": []
                }
        except:
            self.leaderboard = {
                "Easy": [],
                "Medium": [],
                "Hard": []
            }

    def save_to_leaderboard(self):
        if not self.game_won:
            return

        # Use masked username for leaderboard (cheat mode shows as "Player 1")
        display_name = self.get_display_username()

        entry = {
            "username": display_name,
            "score": self.score,
            "time": self.elapsed_time,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "hints_used": 3 - self.hints_remaining
        }

        diff_name = self.difficulty.display_name

        if diff_name not in self.leaderboard:
            self.leaderboard[diff_name] = []

        self.leaderboard[diff_name].append(entry)
        self.leaderboard[diff_name].sort(key=lambda x: x['score'], reverse=True)
        self.leaderboard[diff_name] = self.leaderboard[diff_name][:10]

        with open(self.leaderboard_file, 'w') as f:
            json.dump(self.leaderboard, f, indent=2)

        # Also submit to global leaderboard if online
        if self.mode == "multiplayer" and self.network and self.network.connected:
            try:
                requests.post(f"{SERVER_URL}/api/leaderboard/submit", json=entry, timeout=2)
            except:
                pass

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw title with username
        if self.cheat_mode:
            title_text = f"MINESWEEPER - {self.username} 🎮"
            title_color = CHEAT_COLOR
        else:
            title_text = f"MINESWEEPER - {self.username}"
            title_color = TEXT_COLOR

        title = self.font_large.render(title_text, True, title_color)
        self.screen.blit(title, (self.padding, self.padding))

        # Draw mode buttons
        for button in self.buttons:
            button.draw(self.screen)

        # Draw multiplayer info
        if self.mode == "multiplayer" and self.network:
            multi_y = self.padding + 100
            if self.network.room_code:
                room_text = f"Room: {self.network.room_code}  Players: {len(self.network.players)}/3"
                if self.network.game_started:
                    room_text += "  [IN GAME]"
                else:
                    room_text += "  [WAITING]"
            else:
                room_text = "Connecting to room..."

            room_surf = self.font_small.render(room_text, True, BUTTON_COLOR)
            self.screen.blit(room_surf, (self.padding + 160, multi_y))

        # Draw game info
        info_y = self.padding + 140
        mines_left = self.difficulty.mines - self.flags_placed

        # Add game mode indicator for Luck Mode
        if self.game_mode == "luck" and self.mode == "multiplayer" and self.network:
            display_username = self.get_display_username()
            if self.network.current_turn:
                if self.network.current_turn == display_username:
                    turn_text = "🎯 YOUR TURN!"
                    turn_color = HINT_COLOR
                else:
                    turn_text = f"⏳ {self.network.current_turn}'s turn"
                    turn_color = TEXT_COLOR
                turn_surf = self.font_medium.render(turn_text, True, turn_color)
                self.screen.blit(turn_surf, (self.padding, info_y))
                info_y += 28

        info_text = f"Mines: {mines_left}   Time: {self.elapsed_time}s   Hints: {self.hints_remaining}"

        if self.game_won:
            info_text += f"   🎉 WON! Score: {self.score}"
        elif self.game_over:
            info_text += "   💥 GAME OVER"

        info_surface = self.font_medium.render(info_text, True, TEXT_COLOR)
        self.screen.blit(info_surface, (self.padding, info_y))

        # Draw game board
        board_x = self.padding
        board_y = self.top_panel_height

        for row in range(self.difficulty.rows):
            for col in range(self.difficulty.cols):
                cell = self.board[row][col]
                x = board_x + col * self.cell_size
                y = board_y + row * self.cell_size
                rect = pygame.Rect(x, y, self.cell_size - 2, self.cell_size - 2)

                is_hint = self.hint_cell and self.hint_cell == (row, col)
                is_hovered = self.hovered_cell == (row, col)
                show_mine_cheat = self.cheat_mode and cell.is_mine and not cell.is_revealed and not cell.is_flagged

                if cell.is_revealed:
                    pygame.draw.rect(self.screen, CELL_REVEALED, rect, border_radius=3)

                    if cell.is_mine:
                        pygame.draw.circle(self.screen, MINE_COLOR,
                                         rect.center, self.cell_size // 4)
                    elif cell.adjacent_mines > 0 and self.game_mode != "luck":
                        # Only show numbers in Standard Mode
                        color = NUMBER_COLORS[cell.adjacent_mines]
                        text = self.font_medium.render(str(cell.adjacent_mines), True, color)
                        text_rect = text.get_rect(center=rect.center)
                        self.screen.blit(text, text_rect)
                else:
                    color = CELL_HOVER if is_hovered and not self.game_over else CELL_HIDDEN
                    pygame.draw.rect(self.screen, color, rect, border_radius=3)

                    if show_mine_cheat:
                        pygame.draw.rect(self.screen, CHEAT_COLOR, rect, 3, border_radius=3)

                    if is_hint:
                        pygame.draw.rect(self.screen, HINT_COLOR, rect, 3, border_radius=3)

                    if cell.is_flagged:
                        flag_points = [
                            (rect.centerx - 5, rect.centery + 6),
                            (rect.centerx - 5, rect.centery - 6),
                            (rect.centerx + 6, rect.centery)
                        ]
                        pygame.draw.polygon(self.screen, FLAG_COLOR, flag_points)
                        pygame.draw.line(self.screen, TEXT_COLOR,
                                       (rect.centerx - 5, rect.centery - 6),
                                       (rect.centerx - 5, rect.centery + 6), 2)

        # Draw leaderboard panel
        self.draw_leaderboard()

        # Draw win/loss overlay if in multiplayer Standard Mode
        if self.mode == "multiplayer" and self.network and self.network.game_result:
            self.draw_game_result_overlay()

        pygame.display.flip()

    def draw_leaderboard(self):
        panel_x = self.padding * 2 + self.difficulty.cols * self.cell_size
        panel_y = self.top_panel_height
        panel_width = self.right_panel_width
        panel_height = self.difficulty.rows * self.cell_size

        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, panel_y, panel_width, panel_height), border_radius=5)

        # Title
        if self.mode == "multiplayer":
            title_text = "RACE STANDINGS"
        else:
            title_text = "LEADERBOARD"

        title = self.font_medium.render(title_text, True, TEXT_COLOR)
        title_rect = title.get_rect(centerx=panel_x + panel_width // 2)
        self.screen.blit(title, (title_rect.x, panel_y + 10))

        # Show multiplayer standings or local leaderboard
        if self.mode == "multiplayer" and self.network and self.network.players:
            entry_y = panel_y + 50

            sorted_players = sorted(self.network.players,
                                   key=lambda p: p.get('score', 0),
                                   reverse=True)

            for i, player in enumerate(sorted_players):
                username = player.get('username', 'Player')[:10]
                score = player.get('score', 0)
                finished = player.get('finished', False)
                ready = player.get('ready', False)

                color = PLAYER_COLORS[i % len(PLAYER_COLORS)]

                status = ""
                if finished:
                    status = "✓"
                elif ready:
                    status = "⚡"

                rank_text = f"{i+1}."
                name_text = f"{username} {status}"
                score_text = f"{score} pts" if finished else "Playing..."

                rank_surf = self.font_small.render(rank_text, True, TEXT_COLOR)
                name_surf = self.font_small.render(name_text, True, color)
                score_surf = self.font_small.render(score_text, True, TEXT_COLOR)

                self.screen.blit(rank_surf, (panel_x + 10, entry_y))
                self.screen.blit(name_surf, (panel_x + 35, entry_y))
                self.screen.blit(score_surf, (panel_x + 150, entry_y))

                entry_y += 25
        else:
            # Show local leaderboard
            diff_name = self.font_small.render(f"{self.difficulty.display_name} Mode", True, BUTTON_COLOR)
            diff_rect = diff_name.get_rect(centerx=panel_x + panel_width // 2)
            self.screen.blit(diff_name, (diff_rect.x, panel_y + 40))

            entries = self.leaderboard.get(self.difficulty.display_name, [])
            entry_y = panel_y + 70

            for i, entry in enumerate(entries[:10]):
                rank_text = f"{i+1}."
                username = entry.get('username', 'Player')[:10]
                score_text = f"{entry['score']} pts"

                rank_surf = self.font_small.render(rank_text, True, TEXT_COLOR)
                name_surf = self.font_small.render(username, True, BUTTON_COLOR)
                score_surf = self.font_small.render(score_text, True, TEXT_COLOR)

                self.screen.blit(rank_surf, (panel_x + 10, entry_y))
                self.screen.blit(name_surf, (panel_x + 35, entry_y))
                self.screen.blit(score_surf, (panel_x + 150, entry_y))

                entry_y += 25

            if not entries:
                no_scores = self.font_small.render("No scores yet!", True, TEXT_COLOR)
                no_scores_rect = no_scores.get_rect(centerx=panel_x + panel_width // 2)
                self.screen.blit(no_scores, (no_scores_rect.x, panel_y + 100))

    def draw_game_result_overlay(self):
        """Draw win/loss overlay for multiplayer games"""
        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        # Result text
        if self.network.game_result == "won":
            result_text = "YOU WIN!"
            result_color = (46, 204, 113)  # Green
            emoji = "🎉"
        else:
            result_text = "Ur Cooked"
            result_color = (231, 76, 60)  # Red
            emoji = "💀"

        # Draw result
        font_huge = pygame.font.Font(None, 96)
        result_surf = font_huge.render(result_text, True, result_color)
        result_rect = result_surf.get_rect(center=(self.width // 2, self.height // 2 - 50))
        self.screen.blit(result_surf, result_rect)

        # Draw emoji
        emoji_surf = font_huge.render(emoji, True, TEXT_COLOR)
        emoji_rect = emoji_surf.get_rect(center=(self.width // 2, self.height // 2 + 50))
        self.screen.blit(emoji_surf, emoji_rect)

        # Instructions
        inst_surf = self.font_medium.render("Press ESC to exit", True, TEXT_COLOR)
        inst_rect = inst_surf.get_rect(center=(self.width // 2, self.height // 2 + 150))
        self.screen.blit(inst_surf, inst_rect)

    def run(self):
        clock = pygame.time.Clock()
        running = True

        # Wait for game to start in multiplayer
        if self.mode == "multiplayer" and self.network:
            waiting = True
            while waiting and not self.network.game_started:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        waiting = False
                        break

                    for button in self.buttons:
                        button.handle_event(event)

                self.draw()
                clock.tick(60)

            # Sync game mode from network
            if self.network.game_started:
                self.game_mode = self.network.game_mode
                print(f"Game started in {self.game_mode} mode")

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                button_clicked = False
                for button in self.buttons:
                    if button.handle_event(event):
                        button_clicked = True
                        break

                if event.type == pygame.MOUSEMOTION:
                    row, col = self.get_cell_from_pos(event.pos)
                    self.hovered_cell = (row, col) if row is not None else None

                if not button_clicked:
                    if event.type == pygame.MOUSEBUTTONDOWN and not self.game_over:
                        row, col = self.get_cell_from_pos(event.pos)
                        if row is not None and col is not None:
                            if event.button == 1:
                                if self.hint_cell and self.hint_cell == (row, col):
                                    self.hint_cell = None
                                self.reveal_cell(row, col)
                            elif event.button == 3:
                                self.toggle_flag(row, col)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F2:
                        self.reset_game()
                    elif event.key == pygame.K_h:
                        self.use_hint()
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            if self.start_time and not self.game_over:
                self.elapsed_time = int(time.time() - self.start_time)

            self.draw()
            clock.tick(60)

        pygame.quit()

        # Disconnect from server
        if self.network:
            self.network.disconnect()

if __name__ == '__main__':
    print("="*60)
    print("        🎮  MINESWEEPER MULTIPLAYER  🎮")
    print("="*60)
    print("\n🎯 Features:")
    print("  • Solo and Multiplayer modes")
    print("  • Race Mode: Same board, fastest wins!")
    print("  • Up to 3 players per room")
    print("  • Global and local leaderboards")
    print("\n🎮 Controls:")
    print("  • Left Click: Reveal cell")
    print("  • Right Click: Flag/unflag cell")
    print("  • H: Use hint")
    print("  • F2: New game")
    print("  • ESC: Quit")
    print("="*60)
    print()

    # Main navigation loop - allows returning to username entry
    while True:
        username = get_username()
        print(f"\n🚀 Welcome, {username}!")

        mode = choose_game_mode()

        if mode == "back":
            print("Returning to username entry...")
            continue

        if mode == "solo":
            print("Starting solo game...\n")
            game = MinesweeperGame(username, mode="solo")
            game.run()
            break
        else:
            print("Connecting to multiplayer server...\n")
            network = NetworkManager()

            if not network.connect():
                print("Failed to connect to server. Starting solo mode instead.")
                game = MinesweeperGame(username, mode="solo")
                game.run()
                break
            else:
                # Multiplayer lobby loop - allows returning to game mode selection
                while True:
                    lobby_choice = multiplayer_lobby()

                    if lobby_choice == "back":
                        print("Returning to game mode selection...")
                        break
                    else:
                        # Create game instance to access username masking
                        temp_game = MinesweeperGame(username, mode="solo")
                        display_username = temp_game.get_display_username()

                        if lobby_choice == "create":
                            # Game mode selection loop - allows returning to lobby
                            while True:
                                game_mode_choice = choose_multiplayer_game_mode()
                                if game_mode_choice == "back":
                                    print("Returning to lobby...")
                                    break
                                else:
                                    network.create_room(display_username, game_mode=game_mode_choice)
                                    if network.room_code:
                                        print(f"\nRoom created! Code: {network.room_code}")
                                        print(f"Game Mode: {game_mode_choice.capitalize()}")
                                        print("Share this code with other players to join!")
                                        game = MinesweeperGame(username, mode="multiplayer", network_manager=network)
                                        game.game_mode = game_mode_choice
                                        game.run()
                                    else:
                                        print("Failed to create room.")
                                    break
                            break
                        elif lobby_choice == "join":
                            room_code = get_room_code()
                            if room_code:
                                network.join_room(room_code, display_username)
                                if network.room_code:
                                    print(f"\nJoined room: {room_code}")
                                    game = MinesweeperGame(username, mode="multiplayer", network_manager=network)
                                    # Game mode will be set from network when game starts
                                    game.run()
                                else:
                                    print("Failed to join room.")
                            break
                break
