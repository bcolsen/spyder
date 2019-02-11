# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Third party imports
from qtpy.QtCore import Qt, QEvent
from qtpy.QtGui import QFont, QTextCursor, QMouseEvent

from pytestqt import qtbot
import pytest

# Local imports
from spyder.plugins.editor.widgets.editor import codeeditor


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def editorbot(qtbot):
    widget = codeeditor.CodeEditor(None)
    widget.setup_editor(linenumbers=True, markers=True, tab_mode=False,
                        font=QFont("Courier New", 10),
                        show_blanks=True, color_scheme='Zenburn',
                        scroll_past_end=True)
    widget.setup_editor(language='Python')
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget

# --- Tests
# -----------------------------------------------------------------------------
# testing lowercase transformation functionality

def test_editor_upper_to_lower(editorbot):
    qtbot, widget = editorbot
    text = 'UPPERCASE'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_lowercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text


def test_editor_lower_to_upper(editorbot):
    qtbot, widget = editorbot
    text = 'uppercase'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_uppercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text


@pytest.mark.parametrize("input_text, expected_text, keypress",
                         [('for i in range(2):\n    ',
                           'for i in range(2):\n\n    ',
                           Qt.Key_Enter),
                          ('myvar = 2 ',
                           'myvar = 2\n',
                           Qt.Key_Enter),
                          ('somecode = 1\nmyvar = 2 ',
                           'somecode = 1\nmyvar = 2',
                           Qt.Key_Up),
                          ('somecode = 1\nmyvar = 2 ',
                           'somecode = 1\nmyvar = 2 ',
                           Qt.Key_Left),
                          ('"""This is a string with important spaces\n    ',
                           '"""This is a string with important spaces\n    \n',
                           Qt.Key_Enter)
                          ])
def test_editor_rstrip_keypress(
        editorbot, input_text, expected_text, keypress):
    """Remove whitespace if we left a line with trailing whitespace
    by keypress,"""
    qtbot, widget = editorbot
    widget.set_text(input_text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    qtbot.keyPress(widget, keypress)
    assert widget.toPlainText() == expected_text


@pytest.mark.parametrize("input_text, expected_text, position",
                         [('somecode = 1\nmyvar = 2 ',
                           'somecode = 1\nmyvar = 2',
                           0),
                          ('somecode = 1\nmyvar = 2 ',
                           'somecode = 1\nmyvar = 2 ',
                           23)
                          ])
def test_editor_rstrip_mousepress(
        editorbot, input_text, expected_text, position):
    """Remove whitespace if we left a line with trailing whitespace
    by mouseclick,"""
    qtbot, widget = editorbot
    widget.set_text(input_text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    cursor = widget.textCursor()
    cursor.setPosition(position)
    pos = widget.cursorRect(cursor).center()
    widget.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, pos,
                                       Qt.LeftButton, Qt.LeftButton,
                                       Qt.NoModifier))
    assert widget.toPlainText() == expected_text
