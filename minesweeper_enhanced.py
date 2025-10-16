import pygame
import random
import time
import json
import os
from datetime import datetime
from enum import Enum

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

class MinesweeperGame:
    def __init__(self):
        self.difficulty = Difficulty.MEDIUM
        self.cell_size = 30
        self.top_panel_height = 140
        self.right_panel_width = 250
        self.padding = 20

        self.setup_window()
        self.load_leaderboard()
        self.reset_game()
        self.create_ui_elements()

    def setup_window(self):
        game_width = self.difficulty.cols * self.cell_size
        game_height = self.difficulty.rows * self.cell_size

        self.width = game_width + self.right_panel_width + self.padding * 3
        self.height = game_height + self.top_panel_height + self.padding * 2

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('Minesweeper Enhanced')

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

        # Control buttons
        game_width = self.difficulty.cols * self.cell_size
        hint_x = game_width - 180 + self.padding
        self.hint_btn = Button(hint_x, button_y, 80, 35, "Hint (H)", self.use_hint)
        self.new_game_btn = Button(hint_x + 90, button_y, 80, 35, "New (F2)", self.reset_game)

        self.buttons = [self.easy_btn, self.medium_btn, self.hard_btn, self.hint_btn, self.new_game_btn]

    def change_difficulty(self, difficulty):
        self.difficulty = difficulty
        self.setup_window()
        self.reset_game()
        self.create_ui_elements()

    def reset_game(self):
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

        cell.is_revealed = True

        if self.first_click:
            self.first_click = False
            self.start_time = time.time()
            self.place_mines(row, col)
            cell = self.board[row][col]

        if cell.is_mine:
            self.game_over = True
            self.reveal_all_mines()
            return

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

    def check_win(self):
        for row in range(self.difficulty.rows):
            for col in range(self.difficulty.cols):
                cell = self.board[row][col]
                if not cell.is_mine and not cell.is_revealed:
                    return

        self.game_won = True
        self.game_over = True
        self.calculate_score()
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
        if os.path.exists(self.leaderboard_file):
            with open(self.leaderboard_file, 'r') as f:
                self.leaderboard = json.load(f)
        else:
            self.leaderboard = {
                "Easy": [],
                "Medium": [],
                "Hard": []
            }

    def save_to_leaderboard(self):
        if not self.game_won:
            return

        entry = {
            "score": self.score,
            "time": self.elapsed_time,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "hints_used": 3 - self.hints_remaining
        }

        diff_name = self.difficulty.display_name
        self.leaderboard[diff_name].append(entry)
        self.leaderboard[diff_name].sort(key=lambda x: x['score'], reverse=True)
        self.leaderboard[diff_name] = self.leaderboard[diff_name][:10]  # Keep top 10

        with open(self.leaderboard_file, 'w') as f:
            json.dump(self.leaderboard, f, indent=2)

    def draw(self):
        self.screen.fill(BG_COLOR)

        # Draw title
        title = self.font_large.render("MINESWEEPER", True, TEXT_COLOR)
        self.screen.blit(title, (self.padding, self.padding))

        # Draw mode buttons
        for button in self.buttons:
            button.draw(self.screen)

        # Draw game info
        info_y = self.padding + 95
        mines_left = self.difficulty.mines - self.flags_placed
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

                # Check if this is the hint cell or hovered cell
                is_hint = self.hint_cell and self.hint_cell == (row, col)
                is_hovered = self.hovered_cell == (row, col)

                if cell.is_revealed:
                    pygame.draw.rect(self.screen, CELL_REVEALED, rect, border_radius=3)

                    if cell.is_mine:
                        pygame.draw.circle(self.screen, MINE_COLOR,
                                         rect.center, self.cell_size // 4)
                    elif cell.adjacent_mines > 0:
                        color = NUMBER_COLORS[cell.adjacent_mines]
                        text = self.font_medium.render(str(cell.adjacent_mines), True, color)
                        text_rect = text.get_rect(center=rect.center)
                        self.screen.blit(text, text_rect)
                else:
                    color = CELL_HOVER if is_hovered and not self.game_over else CELL_HIDDEN
                    pygame.draw.rect(self.screen, color, rect, border_radius=3)

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

        pygame.display.flip()

    def draw_leaderboard(self):
        panel_x = self.padding * 2 + self.difficulty.cols * self.cell_size
        panel_y = self.top_panel_height
        panel_width = self.right_panel_width
        panel_height = self.difficulty.rows * self.cell_size

        # Panel background
        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, panel_y, panel_width, panel_height), border_radius=5)

        # Title
        title = self.font_medium.render("LEADERBOARD", True, TEXT_COLOR)
        title_rect = title.get_rect(centerx=panel_x + panel_width // 2)
        self.screen.blit(title, (title_rect.x, panel_y + 10))

        # Difficulty tabs
        diff_name = self.font_small.render(f"{self.difficulty.display_name} Mode", True, BUTTON_COLOR)
        diff_rect = diff_name.get_rect(centerx=panel_x + panel_width // 2)
        self.screen.blit(diff_name, (diff_rect.x, panel_y + 40))

        # Leaderboard entries
        entries = self.leaderboard.get(self.difficulty.display_name, [])
        entry_y = panel_y + 70

        for i, entry in enumerate(entries[:10]):
            rank_text = f"{i+1}."
            score_text = f"{entry['score']} pts"
            time_text = f"{int(entry['time'])}s"

            rank = self.font_small.render(rank_text, True, TEXT_COLOR)
            score = self.font_small.render(score_text, True, BUTTON_COLOR)
            time = self.font_small.render(time_text, True, TEXT_COLOR)

            self.screen.blit(rank, (panel_x + 10, entry_y))
            self.screen.blit(score, (panel_x + 40, entry_y))
            self.screen.blit(time, (panel_x + 150, entry_y))

            entry_y += 25

        if not entries:
            no_scores = self.font_small.render("No scores yet!", True, TEXT_COLOR)
            no_scores_rect = no_scores.get_rect(centerx=panel_x + panel_width // 2)
            self.screen.blit(no_scores, (no_scores_rect.x, panel_y + 100))

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # Handle button events
                for button in self.buttons:
                    button.handle_event(event)

                if event.type == pygame.MOUSEMOTION:
                    row, col = self.get_cell_from_pos(event.pos)
                    self.hovered_cell = (row, col) if row is not None else None

                elif event.type == pygame.MOUSEBUTTONDOWN and not self.game_over:
                    row, col = self.get_cell_from_pos(event.pos)
                    if row is not None and col is not None:
                        if event.button == 1:  # Left click
                            if self.hint_cell and self.hint_cell == (row, col):
                                self.hint_cell = None
                            self.reveal_cell(row, col)
                        elif event.button == 3:  # Right click
                            self.toggle_flag(row, col)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F2:
                        self.reset_game()
                    elif event.key == pygame.K_h:
                        self.use_hint()
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            # Update timer
            if self.start_time and not self.game_over:
                self.elapsed_time = int(time.time() - self.start_time)

            self.draw()
            clock.tick(60)

        pygame.quit()

if __name__ == '__main__':
    print("="*60)
    print("        🎮  MINESWEEPER ENHANCED  🎮")
    print("="*60)
    print("\n🎯 Features:")
    print("  • Three difficulty modes (Easy, Medium, Hard)")
    print("  • Hint system (3 hints per game)")
    print("  • Scoring based on time and hints used")
    print("  • Leaderboard for each difficulty")
    print("\n🎮 Controls:")
    print("  • Left Click: Reveal cell")
    print("  • Right Click: Flag/unflag cell")
    print("  • H: Use hint")
    print("  • F2: New game")
    print("  • ESC: Quit")
    print("="*60)
    print("\n🚀 Starting game...\n")

    game = MinesweeperGame()
    game.run()
