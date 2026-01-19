import unittest
from ui.widgets import hex_editor_widget


class CursorTest(unittest.TestCase):
    def setUp(self):
        self.sut = hex_editor_widget._Cursor()

    def configure_sut(self, bytes_in_group: int, groups_per_row: int, data_size: int=None):
        self.sut.positions_in_group = bytes_in_group * 2
        self.sut.positions_in_row = self.sut.positions_in_group * groups_per_row + 1
        if data_size is not None:
            bytes_per_row = bytes_in_group * groups_per_row
            rows = data_size // bytes_per_row
            remainder_bytes = data_size % bytes_per_row
            max_position = rows * self.sut.positions_in_row
            if remainder_bytes > 0:
                max_position += remainder_bytes * 2
            self.sut.max_position = max_position

    def test_position_is_clamped_to_min_max_position(self):
        self.sut.max_position = 4
        self.sut.position = 5
        self.assertEqual(self.sut.position, 4)
        self.sut.position = -1
        self.assertEqual(self.sut.position, 0)

    def test_row_positions(self):
        self.configure_sut(bytes_in_group=4, groups_per_row=4, data_size=56)
        self.assertEqual(self.sut.row_positions(0), (0, 32))
        self.assertEqual(self.sut.row_positions(1), (33, 65))
        self.assertEqual(self.sut.row_positions(2), (66, 98))
        self.assertEqual(self.sut.row_positions(3), (99, 115))

    def test_position_to_grid(self):
        self.configure_sut(bytes_in_group=2, groups_per_row=4)
        self.assertEqual(self.sut.position_to_grid(0), (0, 0, 0))
        self.assertEqual(self.sut.position_to_grid(1), (0, 0, 1))
        self.assertEqual(self.sut.position_to_grid(3), (0, 0, 3))
        self.assertEqual(self.sut.position_to_grid(4), (0, 1, 0))
        self.assertEqual(self.sut.position_to_grid(16), (0, 3, 4))
        self.assertEqual(self.sut.position_to_grid(17), (1, 0, 0))

    def test_grid_to_position(self):
        self.configure_sut(bytes_in_group=4, groups_per_row=3)
        self.assertEqual(self.sut.grid_to_position(row=0, group=2, nibble=4), 20)
        self.assertEqual(self.sut.grid_to_position(row=2, group=1, nibble=3), 61)

    def test_can_move_by(self):
        self.configure_sut(bytes_in_group=1, groups_per_row=16, data_size=16)
        self.sut.position = 20
        self.assertTrue(self.sut.can_move_by(1))
        self.assertTrue(self.sut.can_move_by(-1))
        self.assertTrue(self.sut.can_move_by(13))
        self.assertFalse(self.sut.can_move_by(14))
        self.assertTrue(self.sut.can_move_by(-20))
        self.assertFalse(self.sut.can_move_by(-21))

    def test_move_to_without_selection(self):
        def test_move_to(position: int, expected_position: int):
            self.sut.move_to(new_position=position, move_anchor=True)
            self.assertEqual(self.sut.position, expected_position)
            self.assertEqual(self.sut.anchor_position, expected_position)

        self.configure_sut(bytes_in_group=2, groups_per_row=8, data_size=32)
        test_move_to(position=-1, expected_position=0)
        test_move_to(position=0, expected_position=0)
        test_move_to(position=5, expected_position=5)
        test_move_to(position=65, expected_position=65)
        test_move_to(position=66, expected_position=66)
        test_move_to(position=67, expected_position=66)

    def test_move_to_with_selection(self):
        def test_move_to(anchor: int, position: int, expected_position: int=None, expected_anchor: int=None):
            self.sut.move_to(new_position=anchor, move_anchor=True)
            self.sut.move_to(new_position=position, move_anchor=False)
            if expected_position is None:
                expected_position = position
            self.assertEqual(self.sut.position, expected_position)
            if expected_anchor is None:
                expected_anchor = anchor
            self.assertEqual(self.sut.anchor_position, expected_anchor)

        self.configure_sut(bytes_in_group=3, groups_per_row=5, data_size=40)
        self.assertEqual(self.sut.positions_in_row, 31)
        test_move_to(anchor=1, position=0, expected_anchor=2)
        test_move_to(anchor=1, position=2, expected_anchor=0)
        test_move_to(anchor=2, position=0, expected_anchor=2)
        test_move_to(anchor=2, position=2, expected_anchor=2)
        test_move_to(anchor=3, position=0, expected_anchor=4)
        test_move_to(anchor=29, position=30, expected_anchor=28)


if __name__ == '__main__':
    unittest.main()
