import keyboard
import pyperclip
import json
import requests
from time import sleep
from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QTextEdit)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QEvent
from PySide6.QtGui import QIcon
import sys
import os
from typing import Optional, Callable

class WindowManager(QObject):
    show_result = Signal(str, str)  # Signal for showing result window (original_text, improved_text)
    show_error = Signal(str)  # Signal for showing error window
    show_message = Signal(str)  # Signal for showing message window
    
    def __init__(self):
        super().__init__()
        self.show_result.connect(self._show_result_window, Qt.QueuedConnection)
        self.show_error.connect(self._show_error_window, Qt.QueuedConnection)
        self.active_windows = []  # Keep track of open windows
        
    def _show_result_window(self, original_text, improved_text):
        # Create window in the main thread
        QApplication.instance().postEvent(self, _ResultWindowEvent(original_text, improved_text))
        
    def _show_error_window(self, error_message):
        # Create window in the main thread
        QApplication.instance().postEvent(self, _ErrorWindowEvent(error_message))

    def event(self, event):
        if isinstance(event, _ResultWindowEvent):
            window = ResultWindow(event.original_text, event.improved_text)
            self.active_windows.append(window)
            window.show()
            return True
        elif isinstance(event, _ErrorWindowEvent):
            window = ErrorWindow(event.error_message)
            self.active_windows.append(window)
            window.show()
            return True
        return super().event(event)

# Custom events for thread-safe window creation
class _ResultWindowEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, original_text, improved_text):
        super().__init__(_ResultWindowEvent.EVENT_TYPE)
        self.original_text = original_text
        self.improved_text = improved_text

class _ErrorWindowEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, error_message):
        super().__init__(_ErrorWindowEvent.EVENT_TYPE)
        self.error_message = error_message

class AcademicImprover:
    def __init__(self, parent=None):
        self.parent = parent
        self.window_manager = None
        self.api_key = None
        self.model = None
        
    def set_window_manager(self, manager):
        self.window_manager = manager

    def improve_text(self, text: str, style: str = "Normal", tone: str = "Friendly", callback: Optional[Callable[[str], None]] = None):
        """
        Improve the given text using AI while maintaining the original language
        
        Args:
            text: The text to improve
            style: Writing style (Normal, Corporate, Academic, Friendly)
            tone: Tone of voice (Enthusiastic, Friendly, Confident, Diplomatic)
            callback: Optional callback function to receive the improved text
        """
        try:
            # Get API key and model from settings
            if not self.parent.settings.get("openrouter_api_key"):
                raise ValueError("OpenRouter API key is not set. Please add it in settings.")
            
            self.api_key = self.parent.settings["openrouter_api_key"]
            self.model = self.parent.settings.get("improver_model", "deepseek/deepseek-r1-distill-llama-70b")
            
            # Detect the language of the input text
            from langdetect import detect
            detected_lang = detect(text)
            
            # Map language codes to full names for clearer instructions
            lang_map = {
                'tr': 'Turkish',
                'en': 'English',
                'de': 'German',
                'fr': 'French',
                'es': 'Spanish',
                'it': 'Italian',
                'ru': 'Russian',
                'ja': 'Japanese',
                'ko': 'Korean',
                'zh-cn': 'Chinese'
            }
            
            language = lang_map.get(detected_lang, 'the original language')
            
            # Prepare system message based on style, tone and detected language
            system_message = f"You are an AI writing assistant. Please improve the given text while keeping it in {language}. "
            system_message += f"Rewrite the text in a {style.lower()} style with a {tone.lower()} tone. "
            system_message += "DO NOT translate the text, only improve its writing style and clarity in the same language. "
            
            if style == "Corporate":
                system_message += f"Use professional business language and formal expressions in {language}. "
            elif style == "Academic":
                system_message += f"Use scholarly language, technical terms, and formal academic writing conventions in {language}. "
            elif style == "Friendly":
                system_message += f"Use casual, warm, and approachable language in {language}. "
                
            if tone == "Enthusiastic":
                system_message += "Express excitement and positivity in the writing."
            elif tone == "Confident":
                system_message += "Use assertive and authoritative language."
            elif tone == "Diplomatic":
                system_message += "Use tactful, balanced, and considerate language."

            # Make API call to OpenRouter
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "AI Writing Assistant"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Please improve this text while keeping it in the same language:\n\n{text}"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                improved_text = result['choices'][0]['message']['content'].strip()
                # Remove any quotes and cleanup the text
                if improved_text.startswith('"') and improved_text.endswith('"'):
                    improved_text = improved_text[1:-1].strip()
                
                # Verify that the improved text is in the same language
                improved_lang = detect(improved_text)
                if improved_lang != detected_lang:
                    raise ValueError(f"The AI generated text in a different language. Please try again.")
                
                # If callback is provided, use it, otherwise show in result window
                if callback:
                    callback(improved_text)
                else:
                    # Show results in popup window
                    self.window_manager.show_result.emit(text, improved_text)
            else:
                raise ValueError("Couldn't get a proper response from AI")

        except Exception as e:
            error_msg = str(e)
            if self.window_manager:
                self.window_manager.show_error.emit(f"Error improving text: {error_msg}")
            raise

class ResultWindow(QMainWindow):
    def __init__(self, original_text, improved_text):
        super().__init__()
        self.setWindowTitle("Academic Text Improvement")
        self.setFixedSize(600, 400)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # Her zaman üstte
        
        # Set window icon
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Orijinal metin
        layout.addWidget(QLabel("Original Text:"))
        original_textedit = QTextEdit()
        original_textedit.setPlainText(original_text)
        original_textedit.setReadOnly(True)
        original_textedit.setMaximumHeight(100)
        original_textedit.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(original_textedit)
        
        # Geliştirilmiş metin
        layout.addWidget(QLabel("Improved Text:"))
        self.improved_textedit = QTextEdit()
        self.improved_textedit.setPlainText(improved_text)
        self.improved_textedit.setReadOnly(True)
        self.improved_textedit.setStyleSheet("""
            QTextEdit {
                background-color: #e8f5e9;
                border: 1px solid #81c784;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.improved_textedit)
        
        # Durum mesajı için label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: green;")
        layout.addWidget(self.status_label)
        
        # Kopyala butonu
        copy_button = QPushButton("Copy Improved Text")
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        copy_button.clicked.connect(self.copy_improved_text)
        layout.addWidget(copy_button)
        
        # Pencereyi ekranın ortasına konumlandır
        self.center_on_screen()
        
    def copy_improved_text(self):
        improved_text = self.improved_textedit.toPlainText()
        pyperclip.copy(improved_text)
        self.status_label.setText("Text copied to clipboard!")
        # 2 saniye sonra mesajı temizle
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))
        
    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

class ErrorWindow(QMainWindow):
    def __init__(self, error_message):
        super().__init__()
        self.setWindowTitle("Error")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # Set window icon
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        error_label = QLabel("Error occurred:")
        layout.addWidget(error_label)
        
        error_text = QTextEdit()
        error_text.setPlainText(error_message)
        error_text.setReadOnly(True)
        error_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffebee;
                border: 1px solid #ef9a9a;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        layout.addWidget(error_text)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        layout.addWidget(close_button)
        
        self.center_on_screen()
        
    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        self.move(x, y)

def main():
    print("Academic Text Improver")
    print("Press ESC to exit")
    
    # Create Qt Application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Create window manager and academic improver in the main thread
    global window_manager
    window_manager = WindowManager()
    academic_improver = AcademicImprover()
    academic_improver.set_window_manager(window_manager)
    window_manager.academic_improver = academic_improver
    
    # Set up keyboard shortcuts
    keyboard.on_press_key('esc', lambda _: app.quit())
    
    # Start Qt event loop
    app.exec()
    
    print("\nExiting Academic Text Improver...")

if __name__ == "__main__":
    main()