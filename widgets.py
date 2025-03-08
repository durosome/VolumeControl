from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from pycaw.pycaw import AudioUtilities

class HotkeyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumWidth(120)
        self.keys = []
        self.modifiers = Qt.KeyboardModifier.NoModifier

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]:
            return

        modifier_names = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            modifier_names.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            modifier_names.append("Shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            modifier_names.append("Alt")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            modifier_names.append("Win")

        key_name = QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)
        
        if event.nativeVirtualKey() >= 0x60 and event.nativeVirtualKey() <= 0x6F:
            key_name = f"Num{key_name}"

        full_sequence = "+".join(modifier_names + [key_name])
        self.setText(full_sequence)
        self.modifiers = modifiers
        self.keys = [key]

class AudioSessionWidget(QListWidgetItem):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.process_name = self.get_clean_process_name()
        self.setText(self.process_name)

    def get_clean_process_name(self):
        try:
            if self.session.Process:
                name = self.session.Process.name()
                return name.strip() if name else "System"
            return "System"
        except:
            return "Unknown"

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_item()
        else:
            super().keyPressEvent(event)

    def delete_selected_item(self):
        if current_item := self.currentItem():
            self.takeItem(self.row(current_item))

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mimeData = self.model().mimeData(self.selectedIndexes())
        drag.setMimeData(mimeData)
        drag.exec(Qt.DropAction.MoveAction)

    def dropEvent(self, event):
        if event.source() == self:
            return super().dropEvent(event)
            
        if event.source().currentItem():
            item_text = event.source().currentItem().text().strip()
            if item_text:
                self.addItem(QListWidgetItem(item_text))
        event.accept()

class EditableTabBar(QTabBar):
    edit_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
        self.editor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.editor.setMinimumWidth(120)
        self.editor.hide()
        self.editor.editingFinished.connect(self.finish_editing)
        self.editor.installEventFilter(self)
        self.current_edit_index = -1

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.editor.hide()
            return True
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event):
        index = self.tabAt(event.pos())
        if index >= 0:
            self.start_edit(index)
        super().mouseDoubleClickEvent(event)

    def start_edit(self, index):
        self.current_edit_index = index
        rect = self.tabRect(index)
        global_pos = self.mapToGlobal(rect.topLeft())
        self.editor.move(global_pos)
        self.editor.resize(max(rect.width(), 120), rect.height())
        self.editor.setText(self.tabText(index))
        self.editor.selectAll()
        self.editor.show()
        self.editor.setFocus()

    def finish_editing(self):
        if self.current_edit_index >= 0:
            new_text = self.editor.text()
            if new_text:
                self.setTabText(self.current_edit_index, new_text)
                self.edit_requested.emit(self.current_edit_index)
            self.editor.hide()
            self.current_edit_index = -1

class EditableLabel(QLabel):
    editingFinished = pyqtSignal()
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(120)
        self.editor = QLineEdit(self)
        self.editor.setWindowFlags(Qt.WindowType.Popup)
        self.editor.setMinimumWidth(120)
        self.editor.hide()
        self.editor.editingFinished.connect(self.finish_editing)
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.editor.hide()
            return True
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_editing()
        super().mouseDoubleClickEvent(event)

    def start_editing(self):
        global_pos = self.mapToGlobal(QPoint(0, 0))
        self.editor.move(global_pos)
        self.editor.resize(max(self.width(), 120), self.height())
        self.editor.setText(self.text())
        self.editor.selectAll()
        self.editor.show()
        self.editor.setFocus()

    def finish_editing(self):
        new_text = self.editor.text()
        if new_text:
            self.setText(new_text)
        self.editor.hide()
        self.editingFinished.emit()