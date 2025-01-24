import os
import sys
import time
import webbrowser
import keyboard
import subprocess
import configparser
import uuid
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QSystemTrayIcon, QMenu, QAction, QVBoxLayout
from PyQt5.QtWidgets import QListWidget, QLineEdit, QHBoxLayout, QComboBox, QLabel
from PyQt5.QtCore import Qt, QTimer, QMetaObject, QPoint, QEvent
from PyQt5.QtGui import QIcon


class SettingsWindow(QWidget):
    def __init__(self, config, button_widget, parent=None):
        super().__init__(parent)
        self.config = config
        self.button_widget = button_widget  # Store the ButtonWidget instance
        self.init_ui()
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    def init_ui(self):
        # Load window size from config
        self.load_window_size()

        main_layout = QHBoxLayout()

        self.list_widget = QListWidget(self)
        self.load_settings()
        self.list_widget.currentItemChanged.connect(self.display_setting)
        main_layout.addWidget(self.list_widget)

        edit_layout = QVBoxLayout()

        self.name_label = QLabel('Name:', self)
        edit_layout.addWidget(self.name_label)
        self.name_input = QLineEdit(self)
        edit_layout.addWidget(self.name_input)

        self.address_label = QLabel('Address:', self)
        edit_layout.addWidget(self.address_label)
        self.address_input = QLineEdit(self)
        self.address_input.setAcceptDrops(True)
        self.address_input.installEventFilter(self)
        edit_layout.addWidget(self.address_input)

        button_layout = QHBoxLayout()
        save_button = QPushButton('保存', self)
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)

        add_button = QPushButton('追加', self)
        add_button.clicked.connect(self.add_setting)
        button_layout.addWidget(add_button)

        delete_button = QPushButton('削除', self)
        delete_button.clicked.connect(self.delete_setting)
        button_layout.addWidget(delete_button)

        self.global_toggle_button = QPushButton('Hide/Show: ON', self)
        self.global_toggle_button.setCheckable(True)
        self.global_toggle_button.setChecked(self.config.getboolean('setting_window', 'toggle', fallback=True))  # Load toggle state from config
        self.global_toggle_button.toggled.connect(self.update_global_toggle_button_text)
        edit_layout.addWidget(self.global_toggle_button)

        edit_layout.addWidget(self.global_toggle_button)  # Add to edit_layout instead of self.layout()
            # Add explanation label below the toggle button
        self.explanation_label = QLabel('Hide/Show ： ボタンを押す毎にアプリを隠す', self)
        edit_layout.addWidget(self.explanation_label)

        edit_layout.addLayout(button_layout)
        main_layout.addLayout(edit_layout)
        self.setLayout(main_layout)
        self.setAcceptDrops(True)

    def eventFilter(self, source, event):
        if event.type() == QEvent.DragEnter and source is self.address_input:
            event.acceptProposedAction()
            return True
        elif event.type() == QEvent.Drop and source is self.address_input:
            mime_data = event.mimeData()
            if mime_data.hasUrls():
                address = mime_data.urls()[0].toString()

                # Check if the action is 'open_file' before replacing slashes
                if 'file:///' in address:
                    # Remove 'file:///' and replace slashes
                    address = address.replace('file:///', '').replace('/', '\\')
                    self.address_input.setText(address.replace('"', ''))
                else:
                    # Handle other cases if needed
                    self.address_input.setText(address.replace('"', ''))
                
                return True
        return super().eventFilter(source, event)

    def update_global_toggle_button_text(self, checked):
        if checked:
            self.global_toggle_button.setText('Hide/Show: ON')
        else:
            self.global_toggle_button.setText('Hide/Show: OFF')
        
        # Save the toggle state to the config file
        if 'setting_window' not in self.config.sections():
            self.config.add_section('setting_window')
        self.config.set('setting_window', 'toggle', str(checked))
        with open('setting.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
            
    def load_settings(self):
        self.config.read('setting.ini', encoding='utf-8')
        self.list_widget.clear()
        for section in self.config.sections():
            name = self.config.get(section, 'name', fallback='')
            if name:
                self.list_widget.addItem(name)

    def display_setting(self, current, previous):
        if current:
            section = current.text()
            for sec in self.config.sections():
                if sec.startswith('Button_') and self.config.get(sec, 'name') == section:
                    self.name_input.setText(section)
                    self.address_input.setText(self.config.get(sec, 'address', fallback=''))
                    self.global_toggle_button.setChecked(self.config.getboolean(sec, 'toggle', fallback=True))
                    self.update_global_toggle_button_text(self.global_toggle_button.isChecked())
                    break

    def save_settings(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            section_name = current_item.text()
            for section in self.config.sections():
                if section.startswith('Button_') and self.config.get(section, 'name') == section_name:
                    self.config.set(section, 'name', self.name_input.text())
                    self.config.set(section, 'address', self.address_input.text())
                    self.config.set(section, 'toggle', str(self.global_toggle_button.isChecked()))
                    with open('setting.ini', 'w', encoding='utf-8') as file:
                        self.config.write(file)
                    current_item.setText(self.name_input.text())
                    
                    # Update the corresponding button in the ButtonWidget
                    for button in self.button_widget.buttons:
                        if button.objectName() == section:
                            button.setText(self.name_input.text())
                            button.setToolTip(f"Address: {self.address_input.text()}")
                            button.adjustSize()
                            break
                    break

    def add_setting(self):
        new_button = f'Button_{uuid.uuid4()}'
        self.config.add_section(new_button)
        self.config.set(new_button, 'name', 'new button')
        self.config.set(new_button, 'address', '')
        self.config.set(new_button, 'x', '200')
        self.config.set(new_button, 'y', '200')
        with open('setting.ini', 'w', encoding='utf-8') as file:
            self.config.write(file)
        self.load_settings()
        
        # Create and add the new button immediately
        button_size = 80
        button = DraggableButton('new button', self.button_widget)
        button.setObjectName(new_button)
        button.setGeometry(100, 100, button_size, button_size)
        button.setStyleSheet(f"background-color: rgba(0, 128, 128, 0.8); color: white; font-size: {button_size // 4}px; padding: 5px;")
        button.clicked.connect(lambda _, s=new_button: self.button_widget.on_button_click(s))
        self.button_widget.buttons.append(button)
        button.adjustSize()
        button.show()

    def delete_setting(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            section_name = current_item.text()
            for section in self.config.sections():
                if section.startswith('Button_') and self.config.get(section, 'name') == section_name:
                    self.config.remove_section(section)
                    with open('setting.ini', 'w', encoding='utf-8') as file:
                        self.config.write(file)
                    break
            self.load_settings()
            
            # Remove the button from the ButtonWidget
            for button in self.button_widget.buttons:
                if button.objectName() == section:
                    button.deleteLater()
                    self.button_widget.buttons.remove(button)
                    break

    def load_window_size(self):
        width = self.config.getint('setting_window', 'width', fallback=400)
        height = self.config.getint('setting_window', 'height', fallback=250)
        cursor_pos = QApplication.instance().desktop().cursor().pos()
        self.setGeometry(cursor_pos.x() - int(width/2), cursor_pos.y()-int(height/2), width, height)

    def save_window_size(self):
        width = self.width()
        height = self.height()
        if 'setting_window' not in self.config.sections():
            self.config.add_section('setting_window')
        self.config.set('setting_window', 'width', str(width))
        self.config.set('setting_window', 'height', str(height))
        with open('setting.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def closeEvent(self, event):
        self.save_window_size()
        event.ignore()
        self.hide()

class DraggableButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self.dragging = False
        self.drag_start_position = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.drag_start_position = event.pos()
        elif event.button() == Qt.RightButton:
            self.dragging = True
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToParent(event.pos() - self.drag_start_position))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self.dragging:
            self.clicked.emit()
        self.dragging = False

class ButtonWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(800, 800)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(10)

        self.load_config()
        self.buttons = []
        self.create_buttons()
        self.load_button_positions()

        self.hide_button = QPushButton("Hide", self)
        self.hide_button.setGeometry(370, 370, 60, 60)
        self.hide_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 0, 0, 0.8);
                color: black;
                font-size: 16px;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.7);
            }
            QPushButton:pressed {
                background-color: rgba(255, 0, 0, 0.9);
            }
        """)
        self.hide_button.clicked.connect(self.hide_widget)

        self.settings_button = QPushButton("Settings", self)
        self.settings_button.setGeometry(370, 440, 60, 60)
        self.settings_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 255, 0.8);
                color: white;
                font-size: 16px;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 255, 0.7);
            }
            QPushButton:pressed {
                background-color: rgba(0, 0, 255, 0.9);
            }
        """)
        self.settings_button.clicked.connect(self.show_settings)

        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_icon.setToolTip("Button Widget")

        self.tray_menu = QMenu(self)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(settings_action)
        self.tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

        self.saving_positions = False
        self.settings_window = None  # Initialize settings window as None

    def showEvent(self, event):
        super().showEvent(event)
        self.load_button_positions()
        self.create_buttons()
        self.setFocus()  # ウィジェットが表示されるたびにフォーカスを設定

    def show_settings(self):
        self.settings_window = SettingsWindow(self.config, self)
        self.settings_window.show()

    def load_config(self):
        self.config = configparser.ConfigParser()
        self.config.read('setting.ini', encoding='utf-8')

    def create_buttons(self):
        sections = [section for section in self.config.sections() if section.startswith('Button_')]
        button_size = 80

        for section in sections:
            if section in self.config:
                button = DraggableButton(self.config[section]['name'], self)
                button.setObjectName(section)
                button.setGeometry(100, 100, button_size, button_size)
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(0, 128, 128, 0.8);
                        color: white;
                        font-size: {button_size // 4}px;
                        padding: 5px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(0, 242, 242, 0.9);
                    }}
                    QPushButton:pressed {{
                        background-color:rgb(42, 42, 42);
                    }}
                """)
                button.adjustSize()
                button.clicked.connect(lambda _, s=section: self.on_button_click(s))
                self.buttons.append(button)

    def on_button_click(self, section):
        if section in self.config:
            address = self.config[section]['address']
            if address.startswith(('http://', 'https://')):
                self.open_browser(address)
            else:
                self.open_file(address)
            
            # Save the button position when clicked
            for button in self.buttons:
                if button.objectName() == section:
                    self.config[section]['x'] = str(button.x())
                    self.config[section]['y'] = str(button.y())
                    with open('setting.ini', 'w', encoding='utf-8') as configfile:
                        self.config.write(configfile)
                    break
            
            # Check the global toggle button state
            if self.settings_window.global_toggle_button.isChecked():
                self.hide()
                self.timer.start(10)

    def update_position(self):
        cursor_pos = QApplication.instance().desktop().cursor().pos()
        self.move(cursor_pos.x() - self.width() // 2, cursor_pos.y() - self.height() // 2)

    def hide_widget(self):
        self.save_button_positions()
        self.hide()
        self.timer.start(10)

    def open_file(self, path):
        subprocess.Popen(['explorer', path])

    def open_browser(self, url):
        webbrowser.open(url)

    def save_button_positions(self):
        if self.saving_positions:
            return
        self.saving_positions = True

        saved_sections = set()

        for button in self.buttons:
            section = button.objectName()
            if section in self.config and section not in saved_sections:
                self.config[section]['x'] = str(button.x())
                self.config[section]['y'] = str(button.y())
                saved_sections.add(section)

        with open('setting.ini', 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

        self.saving_positions = False

    def load_button_positions(self):
        for button in self.buttons:
            section = button.objectName()
            if section in self.config:
                x = int(self.config[section].get('x', button.x()))
                y = int(self.config[section].get('y', button.y()))
                button.move(x, y)
                
                # Load additional information
                name = self.config[section].get('name', button.text())
                address = self.config[section].get('address', '')

                # Update button text and other properties if needed
                button.setText(name)
                button.setToolTip(f"Address: {address}")
                button.adjustSize()

def show_button_widget(widget):
    QMetaObject.invokeMethod(widget, "show", Qt.QueuedConnection)
    time.sleep(0.1)
    QMetaObject.invokeMethod(widget.timer, "stop", Qt.QueuedConnection)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    button_widget = ButtonWidget()
    button_widget.show_settings()
    button_widget.settings_window.close()
    keyboard.add_hotkey('ctrl+space', show_button_widget, args=[button_widget])
    sys.exit(app.exec_())