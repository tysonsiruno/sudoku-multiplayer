import random
import dataclasses
import time
from typing import Iterable

MAX_MINES_PCT = 0.5
MIN_FIELD_SIZE = 5
MAX_FIELD_SIZE = 64


@dataclasses.dataclass
class Cell:
    content: int  # 0 - no mines around, 8 - 8 mines around, -1 - mine, -2 - exploded mine
    state: int  # 0 - hidden, 1 - revealed, 2 - flagged, 3 - false flagged


_field: list[list[Cell]] = None
_width: int = 9
_height: int = 9
_mine_count: int = 0
_flags_count: int = 0
_revealed_count: int = 0
_start_time: float = None
_victory: bool = False
_game_over: bool = False
_game_finish_time: int = None

_preview_pos: tuple[int, int] = None

# Hint system variables
_hints_remaining: int = 3
_hint_cell: tuple[int, int] = None
_show_hint_popup: bool = False
_hint_popup_timer: float = 0


def get_field_width() -> int:
    return _width


def get_field_height() -> int:
    return _height


def get_mines_left() -> int:
    return max(_mine_count - _flags_count, 0)


def get_time() -> int:
    if _game_over or _victory:
        return _game_finish_time
    if _start_time is None:
        return 0
    return int(time.monotonic() - _start_time)


def get_cell_state(x: int, y: int) -> tuple[int, int]:
    return _field[x][y].content, _field[x][y].state


def game_won() -> bool:
    return _victory


def game_over() -> bool:
    return _game_over


def start_game(width: int, height: int, mine_count: int):
    global _width, _height, _field, _mine_count, _flags_count, _revealed_count, _start_time, _victory, _game_over, _game_finish_time, _preview_pos, _hints_remaining, _hint_cell, _show_hint_popup, _hint_popup_timer

    if width < MIN_FIELD_SIZE or height < MIN_FIELD_SIZE:
        raise ValueError(f'Requested field size is too small.\nMinimum dimension is {MIN_FIELD_SIZE}')
    if width > MAX_FIELD_SIZE or height > MAX_FIELD_SIZE:
        raise ValueError(f'Requested field size is too big.\nMaximum dimension is {MAX_FIELD_SIZE}')
    if mine_count > width * height * MAX_MINES_PCT:
        raise ValueError(f'Requested mine count is too large.\n Mine count cannot exceed cell count times {MAX_MINES_PCT}')

    _width = width
    _height = height
    _field = [[Cell(content=0, state=0) for _ in range(height)] for _ in range(width)]

    c = 0
    while c < mine_count:
        x, y = random.randint(0, width - 1), random.randint(0, height - 1)
        if _field[x][y].content != 0:
            continue
        _field[x][y].content = -1
        c += 1

    for x in range(width):
        for y in range(height):
            if _field[x][y].content != 0:
                continue

            _field[x][y].content = _count_neighbor_mines(x, y)

    _mine_count = mine_count
    _flags_count = _revealed_count = 0
    _victory = _game_over = False
    _start_time = _game_finish_time = None
    _preview_pos = None
    _hints_remaining = 3
    _hint_cell = None
    _show_hint_popup = False
    _hint_popup_timer = 0


def iter_neighbors(x: int, y: int) -> Iterable[tuple[int, int]]:
    if y > 0:
        yield x, y - 1
    if y < _height - 1:
        yield x, y + 1

    if x > 0:
        yield x - 1, y
        if y > 0:
            yield x - 1, y - 1
        if y < _height - 1:
            yield x - 1, y + 1

    if x < _width - 1:
        yield x + 1, y
        if y > 0:
            yield x + 1, y - 1
        if y < _height - 1:
            yield x + 1, y + 1


def _count_neighbor_mines(x: int, y: int) -> int:
    count = 0
    for i, j in iter_neighbors(x, y):
        count += _field[i][j].content == -1
    return count


def _count_neighbor_flags(x: int, y: int) -> int:
    count = 0
    for i, j in iter_neighbors(x, y):
        count += _field[i][j].state == 2
    return count


def flag_cell(x: int, y: int):
    global _flags_count

    if _game_over or _victory:
        return

    if _field[x][y].state == 1:
        return

    if _field[x][y].state == 2:
        _field[x][y].state = 0
        _flags_count -= 1
    else:
        _field[x][y].state = 2
        _flags_count += 1


def cell_up(x: int, y: int):
    if _game_over or _victory:
        return

    if _field[x][y].state == 0:
        reveal_cell(x, y)
    elif _field[x][y].state == 1 and _field[x][y].content > 0:
        if _count_neighbor_flags(x, y) != _field[x][y].content:
            return
        for i, j in iter_neighbors(x, y):
            reveal_cell(i, j)


def reveal_cell(x: int, y: int):
    global _start_time, _game_over, _game_finish_time, _victory

    if _game_over or _victory:
        return

    if _field[x][y].state == 2 or _field[x][y].state == 1:
        return

    if _field[x][y].content == -1:
        if _start_time is not None:
            _field[x][y].content = -2
            _game_finish_time = get_time()
            _game_over = True
            game_over_reveal()
            return

        while True:
            new_x, new_y = random.randint(0, _width - 1), random.randint(0, _height - 1)
            if new_x == x and new_y == y:
                continue
            if _field[new_x][new_y].content < 0:
                continue

            _field[x][y].content = _count_neighbor_mines(x, y)
            for i, j in iter_neighbors(x, y):
                if _field[i][j].content >= 0:
                    _field[i][j].content = _count_neighbor_mines(i, j)

            _field[new_x][new_y].content = -1
            for i, j in iter_neighbors(new_x, new_y):
                if _field[i][j].content >= 0:
                    _field[i][j].content = _count_neighbor_mines(i, j)
            break

    if _start_time is None:
        _start_time = time.monotonic()

    reveal_emply_cell(x, y)

    if _width * _height - _mine_count == _revealed_count:
        # Victory!
        _game_finish_time = get_time()
        _victory = True
        victory_flag()


def reveal_emply_cell(x: int, y: int):
    global _revealed_count

    if _field[x][y].content > 0:
        if _field[x][y].state == 0:
            _field[x][y].state = 1
            _revealed_count += 1
        return

    visited: set[tuple[int, int]] = set()
    to_visit: list[tuple[int, int]] = [(x, y)]
    while len(to_visit) > 0:
        x, y = to_visit.pop()
        if x < 0 or y < 0 or x >= _width or y >= _height:
            continue
        if (x, y) in visited:
            continue

        if _field[x][y].state == 0:
            _field[x][y].state = 1
            _revealed_count += 1
        visited.add((x, y))

        if _field[x][y].content != 0:
            continue
        to_visit.extend(
            (
                (x - 1, y),
                (x + 1, y),
                (x - 1, y - 1),
                (x + 1, y + 1),
                (x - 1, y + 1),
                (x + 1, y - 1),
                (x, y - 1),
                (x, y + 1),
            )
        )


def game_over_reveal():
    for row in _field:
        for cell in row:
            if -2 <= cell.content <= -1 and cell.state == 0:
                cell.state = 1
            if 0 <= cell.content <= 8 and cell.state == 2:
                cell.state = 3


def victory_flag():
    global _flags_count
    for row in _field:
        for cell in row:
            if cell.content == -1:
                cell.state = 2
    _flags_count = _mine_count


def set_preview(x: int, y: int):
    global _preview_pos
    if _game_over or _victory:
        return

    if 0 <= _field[x][y].state <= 1:
        _preview_pos = x, y
    else:
        _preview_pos = None


def clear_preview():
    global _preview_pos
    _preview_pos = None


def in_preview(x: int, y: int):
    if _preview_pos is None:
        return False

    if _field[_preview_pos[0]][_preview_pos[1]].state == 0:  # hidden
        return (x, y) == _preview_pos
    elif _field[_preview_pos[0]][_preview_pos[1]].state == 1 and _field[_preview_pos[0]][_preview_pos[1]].content > 0:  # number
        return abs(x - _preview_pos[0]) < 2 and abs(y - _preview_pos[1]) < 2 and _field[x][y].state == 0
    return False


def is_preview():
    if _game_over or _victory:
        return
    return _preview_pos is not None


# Hint system functions
def get_hints_remaining() -> int:
    return _hints_remaining


def get_hint_cell() -> tuple[int, int]:
    return _hint_cell


def clear_hint():
    global _hint_cell
    _hint_cell = None


def show_hint_popup() -> bool:
    return _show_hint_popup


def set_hint_popup(show: bool):
    global _show_hint_popup, _hint_popup_timer
    _show_hint_popup = show
    if show:
        _hint_popup_timer = time.monotonic()


def update_hint_popup():
    global _show_hint_popup
    if _show_hint_popup and time.monotonic() - _hint_popup_timer > 0.1:  # Check frequently
        pass  # Keep showing until user responds


def has_logical_moves() -> bool:
    """Check if there are any safe logical moves available"""
    if _game_over or _victory or _start_time is None:
        return True  # Game not started or finished

    # Check for cells that can be logically determined
    for x in range(_width):
        for y in range(_height):
            cell = _field[x][y]

            # Skip if not revealed or is a mine
            if cell.state != 1 or cell.content <= 0:
                continue

            # Count neighbors
            hidden_neighbors = []
            flagged_count = 0

            for nx, ny in iter_neighbors(x, y):
                neighbor = _field[nx][ny]
                if neighbor.state == 2:  # Flagged
                    flagged_count += 1
                elif neighbor.state == 0:  # Hidden
                    hidden_neighbors.append((nx, ny))

            # If all mines are flagged and there are hidden cells, those are safe
            if flagged_count == cell.content and len(hidden_neighbors) > 0:
                return True

            # If remaining hidden cells equals remaining mines, all are mines
            remaining_mines = cell.content - flagged_count
            if remaining_mines == len(hidden_neighbors) and remaining_mines > 0:
                return True

    return False


def find_safe_hint() -> tuple[int, int]:
    """Find a safe cell to reveal as a hint"""
    # First, look for cells that are logically safe
    for x in range(_width):
        for y in range(_height):
            cell = _field[x][y]

            # Skip if not revealed or is a mine
            if cell.state != 1 or cell.content <= 0:
                continue

            # Count neighbors
            hidden_neighbors = []
            flagged_count = 0

            for nx, ny in iter_neighbors(x, y):
                neighbor = _field[nx][ny]
                if neighbor.state == 2:  # Flagged
                    flagged_count += 1
                elif neighbor.state == 0:  # Hidden
                    hidden_neighbors.append((nx, ny))

            # If all mines are flagged, hidden neighbors are safe
            if flagged_count == cell.content and len(hidden_neighbors) > 0:
                # Return a safe cell that isn't a mine
                for hx, hy in hidden_neighbors:
                    if _field[hx][hy].content >= 0:  # Not a mine
                        return (hx, hy)

    # If no logical move, find any safe unrevealed cell
    safe_cells = []
    for x in range(_width):
        for y in range(_height):
            if _field[x][y].state == 0 and _field[x][y].content >= 0:
                safe_cells.append((x, y))

    if safe_cells:
        return random.choice(safe_cells)

    return None


def use_hint():
    """Use a hint - directly highlight a safe cell"""
    global _hints_remaining, _hint_cell

    if _game_over or _victory or _start_time is None:
        return False

    if _hints_remaining <= 0:
        return False

    # Find and highlight a safe cell
    safe_cell = find_safe_hint()
    if safe_cell:
        _hint_cell = safe_cell
        _hints_remaining -= 1
        return True

    return False


def accept_hint():
    """Accept the hint and highlight a safe cell"""
    global _hints_remaining, _hint_cell

    if _hints_remaining <= 0:
        return False

    safe_cell = find_safe_hint()
    if safe_cell:
        _hint_cell = safe_cell
        _hints_remaining -= 1
        set_hint_popup(False)
        return True

    return False


def decline_hint():
    """Decline the hint offer"""
    set_hint_popup(False)
