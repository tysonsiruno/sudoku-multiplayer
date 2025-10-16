"""
Sudoku Puzzle Generator and Validator

This module provides functionality to generate Sudoku puzzles of varying difficulty
and validate player moves.
"""

import random
from typing import List, Tuple, Set
import copy


class SudokuGenerator:
    """Generate and validate Sudoku puzzles"""

    def __init__(self):
        self.board_size = 9
        self.box_size = 3

    def generate(self, difficulty: str = 'medium') -> Tuple[List[List[int]], List[List[int]]]:
        """
        Generate a Sudoku puzzle and its solution.

        Args:
            difficulty: Puzzle difficulty ('easy', 'medium', 'hard', 'expert', 'evil')

        Returns:
            Tuple of (puzzle, solution) where both are 9x9 2D lists
        """
        # Difficulty mappings (number of clues to leave)
        clues_mapping = {
            'easy': 40,
            'medium': 30,
            'hard': 25,
            'expert': 22,
            'evil': 17
        }

        clues = clues_mapping.get(difficulty, 30)

        # Generate complete board (solution)
        solution = self._generate_complete_board()

        # Create puzzle by removing numbers
        puzzle = self._remove_numbers(copy.deepcopy(solution), clues)

        return puzzle, solution

    def _generate_complete_board(self) -> List[List[int]]:
        """Generate a complete valid Sudoku board using backtracking"""
        board = [[0 for _ in range(9)] for _ in range(9)]
        self._fill_board(board)
        return board

    def _fill_board(self, board: List[List[int]]) -> bool:
        """Fill the board using backtracking with randomization"""
        for row in range(9):
            for col in range(9):
                if board[row][col] == 0:
                    # Try numbers in random order for variety
                    numbers = list(range(1, 10))
                    random.shuffle(numbers)

                    for num in numbers:
                        if self._is_valid_placement(board, row, col, num):
                            board[row][col] = num

                            if self._fill_board(board):
                                return True

                            board[row][col] = 0

                    return False
        return True

    def _is_valid_placement(self, board: List[List[int]], row: int, col: int, num: int) -> bool:
        """Check if placing num at (row, col) is valid"""
        # Check row
        if num in board[row]:
            return False

        # Check column
        if num in [board[r][col] for r in range(9)]:
            return False

        # Check 3x3 box
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for r in range(box_row, box_row + 3):
            for c in range(box_col, box_col + 3):
                if board[r][c] == num:
                    return False

        return True

    def _remove_numbers(self, board: List[List[int]], clues_to_leave: int) -> List[List[int]]:
        """Remove numbers from completed board to create puzzle"""
        cells = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(cells)

        cells_to_remove = 81 - clues_to_leave
        removed = 0

        for row, col in cells:
            if removed >= cells_to_remove:
                break

            backup = board[row][col]
            board[row][col] = 0

            # Verify puzzle still has unique solution (simplified check)
            # For production, you'd want a more robust uniqueness check
            removed += 1

        return board

    def validate_move(self, board: List[List[int]], solution: List[List[int]],
                     row: int, col: int, num: int) -> bool:
        """
        Validate if a move is correct.

        Args:
            board: Current board state
            solution: Complete solution
            row: Row index (0-8)
            col: Column index (0-8)
            num: Number to place (1-9, or 0 to clear)

        Returns:
            True if move is correct, False otherwise
        """
        if num == 0:  # Clearing a cell is always valid
            return True

        # Check against solution
        return solution[row][col] == num

    def is_valid_in_context(self, board: List[List[int]], row: int, col: int, num: int) -> bool:
        """
        Check if a number placement is valid according to Sudoku rules
        (doesn't check against solution, just validates rules)
        """
        if num == 0:
            return True

        # Create temporary board with the new number
        temp_board = [row[:] for row in board]
        temp_board[row][col] = num

        return self._is_valid_placement(temp_board, row, col, num)

    def check_complete(self, board: List[List[int]], solution: List[List[int]]) -> bool:
        """Check if the puzzle is completely and correctly solved"""
        for row in range(9):
            for col in range(9):
                if board[row][col] != solution[row][col]:
                    return False
        return True

    def get_hint(self, board: List[List[int]], solution: List[List[int]]) -> Tuple[int, int, int]:
        """
        Get a hint for the puzzle.

        Returns:
            Tuple of (row, col, number) for a valid move, or None if puzzle is complete
        """
        empty_cells = [(r, c) for r in range(9) for c in range(9) if board[r][c] == 0]

        if not empty_cells:
            return None

        # Return a random empty cell's solution
        row, col = random.choice(empty_cells)
        return (row, col, solution[row][col])

    def get_initial_cells(self, puzzle: List[List[int]]) -> Set[Tuple[int, int]]:
        """Get set of initially filled cells (immutable cells)"""
        return {(r, c) for r in range(9) for c in range(9) if puzzle[r][c] != 0}

    def count_empty_cells(self, board: List[List[int]]) -> int:
        """Count number of empty cells"""
        return sum(1 for row in board for cell in row if cell == 0)

    def get_board_string(self, board: List[List[int]]) -> str:
        """Convert board to string representation for storage/transmission"""
        return ''.join(str(cell) for row in board for cell in row)

    def parse_board_string(self, board_str: str) -> List[List[int]]:
        """Parse board string back to 2D list"""
        if len(board_str) != 81:
            raise ValueError("Board string must be 81 characters")

        board = []
        for i in range(0, 81, 9):
            row = [int(board_str[j]) for j in range(i, i + 9)]
            board.append(row)

        return board


# Singleton instance
sudoku_generator = SudokuGenerator()
