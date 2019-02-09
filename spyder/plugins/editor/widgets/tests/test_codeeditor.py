# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QFont, QTextCursor
                            
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

def test_editor_remove_empty_line(editorbot):
    qtbot, widget = editorbot
    text = 'for i in range(2):\n    '
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    qtbot.keyPress(widget, Qt.Key_Enter)
    expected_text = 'for i in range(2):\n\n    '
    assert widget.toPlainText() == expected_text

def test_editor_remove_trailing_whitespace(editorbot):
    qtbot, widget = editorbot
    text = 'myvar = 2 '
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    qtbot.keyPress(widget, Qt.Key_Enter)
    expected_text = 'myvar = 2\n'
    assert widget.toPlainText() == expected_text

def test_editor_remove_trailing_whitespace_up(editorbot):
    qtbot, widget = editorbot
    text = 'somecode = 1\nmyvar = 2 '
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    qtbot.keyPress(widget, Qt.Key_Up)
    expected_text = 'somecode = 1\nmyvar = 2'
    assert widget.toPlainText() == expected_text

def test_editor_keep_string_empty_line(editorbot):
    qtbot, widget = editorbot
    text = '"""This is a string with important spaces\n    '
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    qtbot.keyPress(widget, Qt.Key_Enter)
    expected_text = '"""This is a string with important spaces\n    \n'
    assert widget.toPlainText() == expected_text
