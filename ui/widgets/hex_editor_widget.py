from contextlib import contextmanager
import dataclasses
import typing
import numpy as np
import numpy.typing as npt
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget


class HexEditorWidgetPalette:
    def __init__(self):
        self.header_bg = QColor(0xf0, 0xf0, 0xf0)
        self.header_fg = QColor(0x00, 0x00, 0xff)
        self.data_cell_bg = QColor(0xff, 0xff, 0xff)
        self.data_cell_fg = QColor(0x00, 0x00, 0x00)
        self.modified_data_cell_bg = QColor(0xff, 0xff, 0xff)
        self.modified_data_cell_fg = QColor(0xff, 0x00, 0x00)
        self.selection_data_bg = QColor(0x00, 0x78, 0xd7)
        self.selection_data_fg = QColor(0x00, 0x00, 0x00)
        self.cursor_fg = QColor(0x00, 0x00, 0x00)

    def header_brush(self) -> QBrush:
        return QBrush(self.header_bg)

    def data_cell_brush(self) -> QBrush:
        return QBrush(self.data_cell_bg)

    def modified_data_cell_brush(self) -> QBrush:
        return QBrush(self.modified_data_cell_bg)


class HexEditorWidget(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._palette = HexEditorWidgetPalette()
        self._data = _Data()
        self._metrics = _Metrics(self._data)
        self._painter = _Painter(self._data, self._metrics)
        self._font = QFont('Consolas')
        self._font.setPixelSize(20)
        self.setFont(self._font)
        self._cursor_timer = QTimer(self)
        self._cursor_timer.setInterval(500)
        self._cursor_timer.setSingleShot(False)
        self._cursor_timer.timeout.connect(self._on_cursor_timer_timeout)

    def setFont(self, font: QFont, /):
        super().setFont(font)
        self._metrics.update(QFontMetrics(font))

    def set_data(self, data: npt.NDArray[np.uint8]):
        self._data.update_data_bytes(data)
        self._metrics.update_data_cells()
        # TODO: remove it
        for i in range(self._data.data_bytes.size):
            if i % 10 == 0:
                self._data.data_bytes[i] = self._data.data_bytes[i] + 2
        self.update()

    def set_column_bytes_count(self, bytes_count: int, group_size: int = None):
        self.set_groups_per_row(groups_per_row=bytes_count // group_size, group_size=group_size)

    def set_groups_per_row(self, groups_per_row: int, group_size: int = None):
        self._data.groups_per_row = groups_per_row
        if group_size is not None:
            self._data.group_size = group_size
            self._data.cursor.positions_in_group = self._data.nibbles_per_group
        self._data.cursor.positions_in_row = self._data.cursor.positions_in_group * groups_per_row + 1
        self._data.update_bytes_per_row()
        self._data.update_rows_number()
        self._update_metrics()
        self.update()

    def palette(self) -> HexEditorWidgetPalette:
        return self._palette

    @contextmanager
    def palette_editor(self) -> HexEditorWidgetPalette:
        try:
            yield self._palette
        finally:
            self.update()

    def _update_metrics(self):
        self._metrics.update(QFontMetrics(self.font()))

    def paintEvent(self, event: QPaintEvent, /):
        super().paintEvent(event)
        painter = QPainter(self)
        self._painter.paint(painter, event, self.palette())

    def keyPressEvent(self, event: QKeyEvent, /):
        move_anchor = not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if event.key() == Qt.Key.Key_Left:
            self._h_shift_cursor_index(-1, move_anchor)
        elif event.key() == Qt.Key.Key_Right:
            self._h_shift_cursor_index(1, move_anchor)
        elif event.key() == Qt.Key.Key_Up:
            self._v_shift_cursor_index(-1, move_anchor)
        elif event.key() == Qt.Key.Key_Down:
            self._v_shift_cursor_index(1, move_anchor, force_clamped_shift=True)
        elif event.key() == Qt.Key.Key_Home:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._data.cursor.move_to(0, move_anchor)
            else:
                row_start_position, _ = self._data.cursor.row_positions(self._data.cursor.current_row)
                self._data.cursor.move_to(row_start_position, move_anchor)
        elif event.key() == Qt.Key.Key_End:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self._data.cursor.move_to(self._data.cursor.max_position, move_anchor)
            else:
                _, row_end_position = self._data.cursor.row_positions(self._data.cursor.current_row)
                self._data.cursor.move_to(row_end_position, move_anchor)
        elif event.key() == Qt.Key.Key_PageUp:
            # TODO: implement it
            pass
        elif event.key() == Qt.Key.Key_PageDown:
            # TODO: implement it
            pass
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent, /):
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event: QMouseEvent, /):
        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_cursor_mouse_click(event.pos())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent, /):
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event, /):
        super().focusInEvent(event)
        #self._cursor_timer.start()

    def focusOutEvent(self, event, /):
        super().focusOutEvent(event)
        self._cursor_timer.stop()
        self._data.cursor_visible = False
        self._repaint_cursor()

    def _handle_cursor_mouse_click(self, pos: QPoint):
        if pos.x() < self._metrics.data_cells.left() or pos.x() > self._metrics.data_cells.right():
            return
        if pos.y() < self._metrics.data_cells.top() or pos.y() > self._metrics.data_cells.bottom():
            return
        y = pos.y() - self._metrics.data_cells.top()
        row = y // self._metrics.row_header.height
        if row >= self._data.rows_number:
            row = self._data.rows_number - 1
        x = pos.x() - self._metrics.data_cells.left()
        group = x // self._metrics.group_header.width
        x = x % self._metrics.group_header.width
        x -= self._metrics.group_header.padding.left
        nibble = x // self._metrics.digit_width
        if nibble < 0:
            nibble = 0
        elif nibble >= self._data.nibbles_per_group:
            nibble = self._data.nibbles_per_group
        print(f"CLICK {row},{group},{nibble}")
        # TODO: check for mouse move?
        self._set_cursor_position(self._data.cursor.grid_to_position(row, group, nibble), move_anchor=True)

    def _on_cursor_timer_timeout(self):
        # TODO: update rect with cursor
        self._data.cursor_visible = not self._data.cursor_visible
        self.update()

    def _h_shift_cursor_index(self, shift: int, move_anchor: bool, force_clamped_shift: bool = False):
        if not force_clamped_shift and not self._data.cursor.can_move_by(shift):
            return
        self._data.cursor.move_by(shift, move_anchor)
        self._on_cursor_index_updated()

    def _v_shift_cursor_index(self, shift: int, move_anchor: bool, force_clamped_shift: bool = False):
        self._h_shift_cursor_index(shift * self._data.cursor.positions_in_row, move_anchor, force_clamped_shift)

    def _set_cursor_position(self, new_position: int, move_anchor: bool):
        print(f"SETTING NEW CURSOR INDEX {new_position}")
        self._data.cursor.move_to(new_position, move_anchor)
        self._on_cursor_index_updated()

    def _on_cursor_index_updated(self):
        self._data.cursor_visible = True
        self._cursor_timer.start()
        self._repaint_cursor()

    def _repaint_cursor(self):
        self.update()


class _Cursor:
    def __init__(self):
        self.visible: bool = False
        self._position: int = 0
        self._anchor_position: int = 0
        self._max_position: int = 0
        self.positions_in_row: int = 1
        self.positions_in_group: int = 1

    @property
    def position(self) -> int:
        return self._position

    @position.setter
    def position(self, position: int):
        self._position = self.clamped_position(position)

    @property
    def anchor_position(self) -> int:
        return self._anchor_position

    @property
    def max_position(self) -> int:
        return self._max_position

    @max_position.setter
    def max_position(self, max_position: int):
        self._max_position = max_position
        self._clamp_position()

    @property
    def max_position_in_row(self) -> int:
        return self.positions_in_row - 1

    @property
    def current_row(self) -> int:
        return self.position // self.positions_in_row

    def row_positions(self, row: int) -> tuple[int, int]:
        start_position = self.upper_clamped_position(row * self.positions_in_row)
        end_position = self.upper_clamped_position(start_position + self.positions_in_row - 1)
        return start_position, end_position

    def position_to_grid(self, position: int) -> tuple[int, int, int]:
        row = position // self.positions_in_row
        in_row_position = position % self.positions_in_row
        group = in_row_position // self.positions_in_group
        if in_row_position != self.max_position_in_row:
            nibble = in_row_position % self.positions_in_group
        else:
            group -= 1
            nibble = self.positions_in_group
        return row, group, nibble

    def grid_to_position(self, row: int, group: int, nibble: int) -> int:
        return row * self.positions_in_row + group * self.positions_in_group + nibble

    def has_selection(self) -> bool:
        return self.position != self._anchor_position

    def can_move_by(self, shift: int) -> bool:
        return 0 <= self.position + shift <= self.max_position

    def move_by(self, shift: int, move_anchor: bool = True):
        self.move_to(self.position + shift, move_anchor)

    def move_to(self, new_position: int, move_anchor: bool = True):
        new_position = self.clamped_position(new_position)
        if not move_anchor:
            selection_direction = 1 if new_position > self.position else -1
            if self.position == self._anchor_position:
                anchor_row, anchor_group, anchor_nibble = self.position_to_grid(self._anchor_position)
                if anchor_nibble % 2 != 0:
                    anchor_nibble -= selection_direction
                self._anchor_position = self.grid_to_position(anchor_row, anchor_group, anchor_nibble)
            cursor_row, cursor_group, cursor_nibble = self.position_to_grid(new_position)
            if cursor_nibble % 2 != 0:
                cursor_nibble += selection_direction
                new_position = self.grid_to_position(cursor_row, cursor_group, cursor_nibble)
        self.position = new_position
        if move_anchor:
            self._anchor_position = self.position

    def clamped_position(self, position: int) -> int:
        return max(0, self.upper_clamped_position(position))

    def upper_clamped_position(self, position: int) -> int:
        return min(position, self.max_position)

    def _clamp_position(self):
        self.position = self.clamped_position(self.position)
        self._anchor_position = self.clamped_position(self._anchor_position)


@dataclasses.dataclass
class _Data:
    address: int = 0x80000000
    data_bytes: npt.NDArray[np.uint8] = dataclasses.field(default_factory=lambda: np.empty(0, dtype=np.uint8))
    original_data_bytes: npt.NDArray[np.uint8] = dataclasses.field(default_factory=lambda: np.empty(0, dtype=np.uint8))
    groups_per_row: int = 1
    group_size: int = 1
    bytes_per_row: int = 1
    rows_number: int = 1
    full_rows_number: int = 1
    cursor: _Cursor = dataclasses.field(default_factory=_Cursor)

    @property
    def nibbles_per_group(self) -> int:
        return self.group_size << 1

    def update_data_bytes(self, data_bytes: npt.NDArray[np.uint8]):
        self.data_bytes = data_bytes.copy()
        self.original_data_bytes = data_bytes.copy()
        self.update_rows_number()
        self.update_cursor_data()

    def update_rows_number(self):
        self.rows_number = \
            (self.data_bytes.size + self.bytes_per_row - 1) // self.bytes_per_row \
            if self.data_bytes.size > self.group_size else \
            1
        self._update_full_rows_number()

    def update_bytes_per_row(self):
        self.bytes_per_row = self.groups_per_row * self.group_size
        self._update_full_rows_number()

    def _update_full_rows_number(self):
        self.full_rows_number = self.data_bytes.size // self.bytes_per_row

    def update_cursor_data(self):
        max_position = self.full_rows_number * self.cursor.positions_in_row
        if self.rows_number > self.full_rows_number:
            max_position += self.non_full_row_bytes_number() * 2 + 1
        self.cursor.max_position = max_position

    def non_full_row_bytes_number(self) -> int:
        return self.data_bytes.size % self.bytes_per_row

    def non_full_row_groups_number(self) -> int:
        return (self.non_full_row_bytes_number() + self.group_size - 1) // self.group_size


_TEXT_VMARGINS = 2


@dataclasses.dataclass
class _Padding:
    left: int
    right: int
    top: int
    bottom: int

    @classmethod
    def even(cls, horiz: int, vert: int) -> typing.Self:
        return _Padding(left=horiz, right=horiz, top=vert, bottom=vert)

    @classmethod
    def empty(cls) -> typing.Self:
        return _Padding.even(horiz=0, vert=0)

    def top_left(self) -> QPoint:
        return QPoint(self.left, self.top)


class _CellMetrics:
    def __init__(self, padding: _Padding = None):
        self.padding = padding or _Padding.empty()
        self.content_size = QSize(0, 0)
        self.size: QSize = self._calculate_size()

    @property
    def width(self) -> int:
        return self.size.width()

    @property
    def height(self) -> int:
        return self.size.height()

    @property
    def content_position(self) -> QPoint:
        return QPoint(self.padding.left, self.padding.top)

    def rect_xy(self, x: int, y: int) -> QRect:
        return self.rect_p(QPoint(x, y))

    def rect_p(self, p: QPoint) -> QRect:
        return QRect(p, self.size)

    def content_rect_xy(self, x: int, y: int) -> QRect:
        return self.content_rect_p(QPoint(x, y))

    def content_rect_p(self, p: QPoint) -> QRect:
        return QRect(p + self.padding.top_left(), self.content_size)

    def update_content_size(self, content_size: QSize):
        self.content_size = content_size
        self._update_size()

    def _update_size(self):
        self.size = self._calculate_size()

    def _calculate_size(self) -> QSize:
        return QSize(
            self.content_size.width() + self.padding.left + self.padding.right,
            self.content_size.height() + self.padding.top + self.padding.bottom)


class _Metrics:
    def __init__(self, data: _Data):
        self._data = data
        self.font_height = 1
        self.row_header = _CellMetrics(_Padding.even(horiz=5, vert=_TEXT_VMARGINS))
        self.group_header = _CellMetrics(_Padding.even(horiz=8, vert=_TEXT_VMARGINS))
        self.row_0 = QRect()
        self.data_cell = self._data_cell_metrics()
        self.data_cells = QRect()
        self.digit_width = 1

    def update(self, font_metrics: QFontMetrics):
        self.font_height = font_metrics.height()
        self.row_header.update_content_size(self._text_size(font_metrics.horizontalAdvance('00000000')))
        data_cell_characters_number = self._data.nibbles_per_group
        group_header_characters_number = len(f'+{self._data.bytes_per_row - 1:x}')
        column_max_characters_number = \
            data_cell_characters_number \
                if data_cell_characters_number >= group_header_characters_number else \
                group_header_characters_number
        column_text_width = font_metrics.horizontalAdvance('0' * column_max_characters_number)
        self.group_header.update_content_size(self._text_size(column_text_width))
        self.row_0 = QRect(
            QPoint(0, 0),
            QSize(
                self.row_header.width + self.group_header.width * self._data.groups_per_row,
                self.group_header.height))
        self.data_cell = self._data_cell_metrics()
        self.update_data_cells()
        self.digit_width = font_metrics.horizontalAdvance('0')

    def update_data_cells(self):
        self.data_cells = QRect(
            self.first_data_cell_position(),
            QSize(
                self.group_header.width * self._data.groups_per_row,
                self.row_header.height * self._data.rows_number))

    def _data_cell_metrics(self) -> _CellMetrics:
        metrics = _CellMetrics(self._data_cell_padding())
        metrics.update_content_size(
            QSize(self.group_header.content_size.width(), self.row_header.content_size.height()))
        return metrics

    def _data_cell_padding(self) -> _Padding:
        return _Padding(
            left=self.group_header.padding.left, right=self.group_header.padding.right,
            top=self.row_header.padding.top, bottom=self.row_header.padding.bottom)

    def first_data_cell_position(self) -> QPoint:
        return QPoint(self.row_header.width, self.group_header.height)

    def data_cell_rect(self, row: int, group: int) -> QRect:
        return self.data_cell.rect_p(self.first_data_cell_position() + self.data_cell_offset(row, group))

    def data_cell_inner_rect(self, row: int, group: int) -> QRect:
        return self.data_cell.content_rect_p(self.first_data_cell_position() + self.data_cell_offset(row, group))

    def data_cell_offset(self, row: int, group: int) -> QPoint:
        return QPoint(group * self.data_cell.width, row * self.data_cell.height)

    def data_cell_position(self, row: int, group: int) -> QPoint:
        return self.first_data_cell_position() + self.data_cell_offset(row, group)

    def data_cell_nibble_top_left(self, row: int, group: int, nibble: int) -> QPoint:
        return self.first_data_cell_position() + self.data_cell_offset(row, group) + \
            self.data_cell.content_position + QPoint(self.digit_width * nibble, 0)

    def data_cell_nibble_bottom_right(self, row: int, group: int, nibble: int) -> QPoint:
        return self.data_cell_nibble_top_left(row, group, nibble) + QPoint(self.digit_width, self.font_height)

    def _text_size(self, width: int) -> QSize:
        return QSize(width, self.font_height)


_ALIGN_LEFT_VCENTER = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


class _Painter:
    def __init__(self, data: _Data, metrics: _Metrics):
        self.data = data
        self.metrics = metrics
        self._painter: typing.Optional[QPainter] = None
        self._event: typing.Optional[QPaintEvent] = None
        self._palette: typing.Optional[HexEditorWidgetPalette] = None

    def paint(self, painter: QPainter, event: QPaintEvent, palette: HexEditorWidgetPalette):
        self._painter = painter
        self._event = event
        self._palette = palette
        self._paint_group_headers()
        self._paint_address_headers()
        self._paint_data_bg()
        self._paint_data()
        self._paint_cursor()
        self._painter = None
        self._event = None
        self._palette = None

    def _paint_address_headers(self):
        header_rect = self.metrics.row_header.rect_xy(0, self.metrics.group_header.height)
        header_height = self.metrics.row_header.height
        bg_brush = self._palette.header_brush()
        self._painter.setPen(self._header_text_pen())
        address = self.data.address
        for row in range(self.data.rows_number):
            self._painter.fillRect(header_rect, bg_brush)
            self._painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, f'{address:08x}')
            address += self.data.bytes_per_row
            header_rect.adjust(0, header_height, 0, header_height)

    def _paint_group_headers(self):
        header_rect = self.metrics.group_header.content_rect_xy(self.metrics.row_header.width, 0)
        header_width = self.metrics.group_header.width
        self._painter.fillRect(self.metrics.row_0, self._palette.header_brush())
        self._painter.setPen(self._header_text_pen())
        for offset in range(0, self.data.bytes_per_row, self.data.group_size):
            self._painter.drawText(header_rect, _ALIGN_LEFT_VCENTER, f'+{offset:x}')
            header_rect.adjust(header_width, 0, header_width, 0)

    def _paint_data_bg(self):
        self._painter.fillRect(self.metrics.data_cells, self._palette.data_cell_brush())
        start = self.metrics.data_cell_nibble_top_left(1, group=0, nibble=1)
        end = self.metrics.data_cell_nibble_bottom_right(1, group=0, nibble=1)
        #self._painter.fillRect(QRect(start, end), QColor(0xff, 0xff, 0x00))


        for row in range(self.data.rows_number):
            for group in range(self.data.groups_per_row):
                for nibble in range(self.data.nibbles_per_group):
                    start = self.metrics.data_cell_nibble_top_left(row, group, nibble)
                    end = self.metrics.data_cell_nibble_bottom_right(row, group, nibble)
                    disc = row + group + nibble
                    self._painter.fillRect(QRect(start, end), (QColor(255, 255, 0) if disc % 2 == 0 else QColor(0, 255, 0)))




        if not self.data.cursor.has_selection():
            return
        cursor = self.data.cursor
        if cursor.anchor_position < cursor.position:
            start_position = cursor.anchor_position
            end_position = cursor.position
        else:
            start_position = cursor.position
            end_position = cursor.anchor_position
        end_position -= 1
        start_row, start_group, start_nibble = cursor.position_to_grid(start_position)
        end_row, end_group, end_nibble = cursor.position_to_grid(end_position)
        start_position = self.metrics.data_cell_nibble_top_left(start_row, start_group, start_nibble)
        end_position = self.metrics.data_cell_nibble_bottom_right(end_row, end_group, end_nibble)
        self._painter.fillRect(QRect(start_position, end_position), self._palette.selection_data_bg)


    def _paint_data(self):
        data_pen = QPen(self._palette.data_cell_fg)
        modified_data_brush = self._palette.modified_data_cell_brush()
        modified_data_pen = QPen(self._palette.modified_data_cell_fg)
        self._painter.setPen(data_pen)
        is_data_pen_in_use = True
        # TODO: add selection fg pen

        temp = 0

        def draw_cell(rect: QRect, inner_rect: QRect):
            nonlocal is_data_pen_in_use
            data_bytes = self.data.data_bytes[data_index:data_index + self.data.group_size]
            original_data_bytes = self.data.original_data_bytes[data_index:data_index + self.data.group_size]
            if np.array_equal(data_bytes, original_data_bytes):
                if not is_data_pen_in_use:
                    self._painter.setPen(data_pen)
                    is_data_pen_in_use = True
            else:
                if is_data_pen_in_use:
                    self._painter.setPen(modified_data_pen)
                    is_data_pen_in_use = False
                #if not selected:
                #    self._painter.fillRect(rect, modified_data_brush)
            data_text = ''.join(f'{b:02x}' for b in data_bytes)
            #self._painter.drawText(inner_rect, _ALIGN_LEFT_VCENTER, data_text)
            nonlocal temp
            #self._painter.fillRect(rect, QColor(0xff, 0x00, 0x00) if temp % 3 == 0 else QColor(0x00, 0xff, 0x00))
            temp += 1
            self._painter.drawText(inner_rect, _ALIGN_LEFT_VCENTER, data_text)

        cell_width = self.metrics.data_cell.width
        cell_height = self.metrics.data_cell.height
        row_first_group_rect = self.metrics.data_cell_rect(row=0, group=0)
        row_first_group_inner_rect = self.metrics.data_cell_inner_rect(row=0, group=0)
        data_index = 0
        for row in range(self.data.full_rows_number):
            cell_rect = QRect(row_first_group_rect)
            cell_inner_rect = QRect(row_first_group_inner_rect)
            for column_index in range(self.data.groups_per_row):
                draw_cell(cell_rect, cell_inner_rect)
                cell_rect.adjust(cell_width, 0, cell_width, 0)
                cell_inner_rect.adjust(cell_width, 0, cell_width, 0)
                data_index += self.data.group_size
            row_first_group_rect.adjust(0, cell_height, 0, cell_height)
            row_first_group_inner_rect.adjust(0, cell_height, 0, cell_height)
        if self.data.rows_number > self.data.full_rows_number:
            cell_rect = row_first_group_rect
            cell_inner_rect = row_first_group_inner_rect
            for column_index in range(self.data.non_full_row_groups_number()):
                draw_cell(cell_rect, cell_inner_rect)
                cell_rect.adjust(cell_width, 0, cell_width, 0)
                cell_inner_rect.adjust(cell_width, 0, cell_width, 0)
                data_index += self.data.group_size

    def _paint_cursor(self):
        if not self.data.cursor.visible:
            return
        pen = QPen(self._palette.cursor_fg)
        pen.setWidth(2)
        self._painter.setPen(pen)
        cursor_position = self._cursor_xy_position(self.data.cursor.position)
        self._painter.drawLine(
            cursor_position.x(), cursor_position.y(),
            cursor_position.x(), cursor_position.y() + self.metrics.font_height)

    def _cursor_xy_position(self, index_position: int) -> QPoint:
        row, group, nibble = self.data.cursor.position_to_grid(index_position)
        xy_position = self.metrics.data_cell_position(row, group)
        xy_position += QPoint(self.metrics.data_cell.padding.left, self.metrics.data_cell.padding.top)
        if nibble > 0:
            xy_position += QPoint(nibble * self.metrics.digit_width, 0)
        return xy_position

    def _header_text_pen(self) -> QPen:
        return QPen(self._palette.header_fg)


if __name__ == '__main__':
    pass
