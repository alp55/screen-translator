import sys
import json
from typing import Optional, Dict
from pathlib import Path
from time import sleep
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                             QVBoxLayout, QSystemTrayIcon, QMenu, QColorDialog,
                             QSpinBox, QCheckBox, QComboBox, QFontComboBox,
                             QPushButton, QKeySequenceEdit, QLineEdit, QPlainTextEdit, 
                             QHBoxLayout, QGridLayout, QTabWidget, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt, QTimer, QPoint, QKeyCombination, QEvent, Signal
from PySide6.QtGui import QFont, QAction, QIcon, QColor, QCursor, QKeySequence
from deep_translator import GoogleTranslator
import deepl
from langdetect import detect
import keyboard
from academic_editor import AcademicImprover, WindowManager  # WindowManager eklendi

COMMON_STYLES = """
    QWidget {
        font-family: 'Segoe UI', Arial;
        font-size: 10pt;
    }
    QLabel {
        color: #2c3e50;
        font-weight: bold;
        margin-top: 5px;
    }
    QPushButton {
        background-color: #2196F3;
        color: white;
        border: none;
        padding: 8px 15px;
        border-radius: 4px;
        font-weight: bold;
        min-width: 100px;
    }
    QPushButton:hover {
        background-color: #1976D2;
    }
    QPushButton:pressed {
        background-color: #0D47A1;
    }
    QComboBox {
        padding: 5px;
        border: 1px solid #bdc3c7;
        border-radius: 3px;
        background: white;
    }
    QComboBox:focus {
        border: 1px solid #3498db;
    }
    QSpinBox, QLineEdit {
        padding: 5px;
        border: 1px solid #bdc3c7;
        border-radius: 3px;
    }
    QSpinBox:focus, QLineEdit:focus {
        border: 1px solid #3498db;
    }
    QPlainTextEdit {
        border: 1px solid #bdc3c7;
        border-radius: 3px;
        padding: 5px;
    }
    QPlainTextEdit:focus {
        border: 1px solid #3498db;
    }
    QCheckBox {
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }
    QCheckBox::indicator:unchecked {
        border: 2px solid #bdc3c7;
        border-radius: 3px;
        background: white;
    }
    QCheckBox::indicator:checked {
        border: 2px solid #2196F3;
        border-radius: 3px;
        background: #2196F3;
    }
    QSpinBox {
        padding: 5px 35px 5px 10px;  /* Sağ tarafta ok için daha fazla boşluk */
        border: 1px solid #bdc3c7;
        border-radius: 3px;
        background: white;
        min-width: 80px;
        min-height: 25px;
        font-size: 11pt;  /* Font boyutu artırıldı */
        margin-bottom: 8px;  /* Alt boşluk eklendi */
    }
    QSpinBox::up-button {
        width: 20px;
        height: 17.5px;
        background: #e1e1e1;
        border: none;
        border-left: 1px solid #bdc3c7;
        image: url(up.png);
        subcontrol-position: top right;
    }
    QSpinBox::down-button {
        width: 20px;
        height: 17.5px;
        background: #e1e1e1;
        border: none;
        border-left: 1px solid #bdc3c7;
        image: url(down.png);
        subcontrol-position: bottom right;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background: #d1d1d1;
    }
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
        background: #c1c1c1;
    }
"""

class TranslationWidget(QMainWindow):
    CACHE_LIMIT = 500  # Sabit cache limiti
    
    def __init__(self):
        super().__init__()
        self.settings_file = Path("settings.json")
        self.translator_cache: Dict[str, str] = {}
        self.last_copied = ''
        self.load_settings()
        self.setup_ui()
        self.setup_tray()
        self.hide()

        # Initialize window manager and academic improver
        self.window_manager = WindowManager()
        self.academic_improver = AcademicImprover(self)
        self.academic_improver.set_window_manager(self.window_manager)

        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        
        self.is_improving = False  # Academic improvement işlemini takip etmek için flag

        # Update translation shortcut based on settings
        self.update_shortcut()

    def update_shortcut(self):
        # Remove any existing keyboard hooks
        keyboard.unhook_all()
        
        # Set up translation shortcut
        shortcut = self.settings.get("keyboard_shortcut", "a")  # Default to 'a' if not set
        keyboard.on_press_key(shortcut, self.simulate_copy)
        
        # Set up improver shortcut if enabled
        if self.settings.get("use_improver", True):
            improve_shortcut = self.settings.get("improve_shortcut", "f2")
            keyboard.on_press_key(improve_shortcut, lambda _: self.improve_selected_text())
            
    def simulate_copy(self, event):
        # Don't trigger copy if we're in improving mode
        if not self.is_improving:
            # Simulate Ctrl+C using keyboard module instead of QTest
            keyboard.send('ctrl+c')
        
    def on_clipboard_change(self):
        # Eğer academic improvement işlemi yapılıyorsa çeviriyi atla
        if self.is_improving:
            return
            
        text = self.clipboard.text()
        if text and text != self.last_copied:
            self.last_copied = text
            self.do_translate(text)

    def load_settings(self):
        default_settings = {
            "show_translation_details": True,
            "text_color": "#000000",
            "font_family": "Arial",
            "font_size": 12,
            "display_time": 5000,
            "target_lang": "tr",
            "window_alpha": 0.9,
            "frame_color": "#F0F0F0",
            "frame_alpha": 0.9,
            "keyboard_shortcut": "a",  # Default shortcut
            "use_deepl": False,
            "deepl_api_key": "",  # New setting for DeepL API key
            "openrouter_api_key": "",  # New setting for OpenRouter API key
            "improve_shortcut": "f2",  # Default shortcut for Academic Improver
            "use_improver": True,  # Academic improver aktif/pasif ayarı
            "improver_model": "deepseek/deepseek-r1-distill-llama-70b",  # Default AI model
            "writing_style": "Normal",  # Default writing style
            "writing_tone": "Friendly"  # Default writing tone
        }

        try:
            if self.settings_file.exists():
                self.settings = {**default_settings, **json.loads(self.settings_file.read_text('utf-8'))}
            else:
                self.settings = default_settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.settings = default_settings

    def save_settings(self):
        try:
            self.settings_file.write_text(json.dumps(self.settings, indent=4, ensure_ascii=False), 'utf-8')
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def setup_ui(self):
        # Pencereyi tamamen frameless ve şeffaf yap
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        # Ana widget'ı ayarla
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout'u oluştur
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(10, 10, 10, 10)  # Kenar boşluklarını ayarla
        
        # Translation label'ı ayarla
        self.translation_label = QLabel()
        self.translation_label.setWordWrap(True)
        self.translation_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.update_label_style()
        
        layout.addWidget(self.translation_label)
        self.resize(400, 100)
        self.update_widget_style()

    def update_label_style(self):
        font = QFont(
            self.settings["font_family"],
            self.settings["font_size"]
        )
        self.translation_label.setFont(font)
        self.translation_label.setStyleSheet(
            f"color: {self.settings['text_color']};"
            f"padding: 10px;"
        )

    def update_widget_style(self):
        frame_color = QColor(self.settings["frame_color"])
        frame_color.setAlphaF(self.settings["frame_alpha"])
        
        # Ana pencereye stil uygula
        style = f"""
            QWidget#centralWidget {{
                background-color: {frame_color.name(QColor.HexArgb)};
                border-radius: 10px;
                border: none;
            }}
        """
        self.central_widget.setObjectName("centralWidget")  # Stil için ID ekle
        self.setStyleSheet(style)
        
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))

        tray_menu = QMenu()
        
        show_action = QAction("Show/Hide", self)
        show_action.triggered.connect(self.toggle_visibility)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)

        # AI Writing Assistant action (opens window directly)
        ai_assistant_action = QAction("AI Writing Assistant", self)  # Removed (F2) from menu text
        ai_assistant_action.triggered.connect(self.show_ai_assistant)
        
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.quit)

        tray_menu.addAction(show_action)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        tray_menu.addAction(ai_assistant_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def set_writing_style(self, style):
        # Uncheck all other styles
        for s, action in self.style_actions.items():
            action.setChecked(s == style)
        self.settings["writing_style"] = style
        self.save_settings()

    def set_writing_tone(self, tone):
        # Uncheck all other tones
        for t, action in self.tone_actions.items():
            action.setChecked(t == tone)
        self.settings["writing_tone"] = tone
        self.save_settings()

    def do_translate(self, text: str):
        try:
            if self.settings["show_translation_details"]:
                words = text.split()
                translations = []
                chunk_size = 5
                
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:min(i + chunk_size, len(words))])
                    translation = self.translate_text(chunk)
                    if translation:
                        translations.append(f"{chunk} → {translation}")
                
                result = "\n".join(translations)
            else:
                result = self.translate_text(text)

            if result:
                self.show_translation(result)

        except Exception as e:
            self.show_error(str(e))

    def translate_text(self, text: str) -> Optional[str]:
        if text in self.translator_cache:
            return self.translator_cache[text]

        try:
            # Only detect language if needed
            detected_lang = detect(text)
            if detected_lang == self.settings["target_lang"]:
                return text

            if self.settings["use_deepl"] and self.settings["deepl_api_key"]:
                try:
                    translator = deepl.Translator(self.settings["deepl_api_key"])
                    result = translator.translate_text(text, target_lang=self.settings["target_lang"].upper())
                    translation = result.text
                except Exception as e:
                    print(f"DeepL translation error: {e}")
                    # Fallback to Google Translate if DeepL fails
                    translator = GoogleTranslator(
                        source='auto',
                        target=self.settings["target_lang"]
                    )
                    translation = translator.translate(text)
            else:
                translator = GoogleTranslator(
                    source='auto',
                    target=self.settings["target_lang"]
                )
                translation = translator.translate(text)
            
            # Cache management
            if len(self.translator_cache) >= self.CACHE_LIMIT:
                # Remove oldest entries to make space
                remove_count = len(self.translator_cache) - self.CACHE_LIMIT + 1
                for _ in range(remove_count):
                    self.translator_cache.pop(next(iter(self.translator_cache)))
            
            self.translator_cache[text] = translation
            return translation
        except Exception as e:
            print(f"Translation error: {e}")
            return None

    def show_translation(self, text: str):
        self.translation_label.setText(text)
        self.adjust_size()
        self.move_to_cursor()
        self.show()
        QTimer.singleShot(self.settings["display_time"], self.hide)

    def show_error(self, error_msg: str):
        self.translation_label.setText(f"Hata: {error_msg}")
        self.adjust_size()
        self.move_to_cursor()
        self.show()
        QTimer.singleShot(5000, self.hide)

    def adjust_size(self):
        text = self.translation_label.text()
        font_metrics = self.translation_label.fontMetrics()
        
        # Optimize size calculations
        padding = 20
        text_width = min(
            800,  # Maximum width
            max(200, font_metrics.horizontalAdvance(text.split('\n')[0]) + padding * 2)
        )
        
        self.translation_label.setFixedWidth(text_width)
        self.translation_label.adjustSize()
        
        window_width = text_width + padding * 2
        window_height = self.translation_label.height() + padding * 2
        
        self.resize(int(window_width), int(window_height))

    def move_to_cursor(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        
        x = min(cursor_pos.x(), screen.width() - self.width())
        y = min(cursor_pos.y() - self.height() - 20, screen.height() - self.height())
        
        self.move(max(0, x), max(0, y))

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def set_target_lang(self, lang: str):
        self.settings["target_lang"] = lang
        self.save_settings()

    def show_settings(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def improve_selected_text(self):
        """Opens the AI Writing Assistant window and processes selected text"""
        if not self.settings.get("use_improver", True):  # If improver is disabled
            self.window_manager.show_error.emit("AI Writing Assistant is disabled. Enable it in settings.")
            return

        # Disconnect clipboard signal temporarily
        self.clipboard.dataChanged.disconnect(self.on_clipboard_change)
        
        # Set improving flag before getting text
        self.is_improving = True
        try:
            # Get selected text directly without using clipboard
            keyboard.send('ctrl+c')
            sleep(0.2)  # Wait for clipboard to update
            text = self.clipboard.text().strip()
            
            if not text:
                self.window_manager.show_error.emit("Please select some text first!")
                return
                
            # Always use Academic style when using F2 shortcut
            self.settings["writing_style"] = "Academic"
            self.settings["writing_tone"] = "Confident"  # Academic yazılar için uygun ton
            self.save_settings()
            
            # Improve text using academic improver
            self.academic_improver.improve_text(
                text,
                style="Academic",
                tone="Confident"
            )
        finally:
            # Reset improving flag and reconnect clipboard
            self.is_improving = False
            self.clipboard.dataChanged.connect(self.on_clipboard_change)

    def show_ai_assistant(self):
        """Shows the AI Writing Assistant window"""
        if not hasattr(self, 'ai_assistant_window'):
            self.ai_assistant_window = AIWritingAssistantWindow(self)
        self.ai_assistant_window.show()
        self.ai_assistant_window.activateWindow()

class AIWritingAssistantWindow(QWidget):
    text_ready = Signal(str)  # Signal for handling improved text
    
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setup_ui()
        self.setWindowTitle("AI Writing Assistant")
        self.setWindowIcon(QIcon("icon.png"))
        
        # Set fixed size and flags
        self.setMinimumSize(800, 600)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Connect text_ready signal
        self.text_ready.connect(self.update_output_text, Qt.QueuedConnection)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header section with icon and title
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(QIcon("icon.png").pixmap(32, 32))
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("AI Writing Assistant")
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Settings section
        settings_group = QWidget()
        settings_layout = QHBoxLayout(settings_group)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(20)
        
        # Model selection
        model_layout = QVBoxLayout()
        model_label = QLabel("AI Model:")
        self.model_combo = QComboBox()
        models = list(SettingsWindow.AI_MODELS.keys())
        self.model_combo.addItems(models)
        current_model = self.parent.settings.get("improver_model")
        current_model_name = [name for name, model in SettingsWindow.AI_MODELS.items() 
                            if model == current_model][0]
        self.model_combo.setCurrentText(current_model_name)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        settings_layout.addLayout(model_layout)
        
        # Style selection
        style_layout = QVBoxLayout()
        style_label = QLabel("Writing Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Normal", "Corporate", "Academic", "Friendly"])
        self.style_combo.setCurrentText(self.parent.settings.get("writing_style", "Normal"))
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        settings_layout.addLayout(style_layout)
        
        # Tone selection
        tone_layout = QVBoxLayout()
        tone_label = QLabel("Tone:")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["Enthusiastic", "Friendly", "Confident", "Diplomatic"])
        self.tone_combo.setCurrentText(self.parent.settings.get("writing_tone", "Friendly"))
        tone_layout.addWidget(tone_label)
        tone_layout.addWidget(self.tone_combo)
        settings_layout.addLayout(tone_layout)
        
        main_layout.addWidget(settings_group)
        
        # Text areas
        text_group = QWidget()
        text_layout = QVBoxLayout(text_group)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(10)
        
        # Input area
        input_label = QLabel("Input Text:")
        self.text_input = QPlainTextEdit()
        self.text_input.setPlaceholderText("Enter your text here...")
        self.text_input.setMinimumHeight(200)
        text_layout.addWidget(input_label)
        text_layout.addWidget(self.text_input)
        
        # Output area
        output_label = QLabel("Improved Text:")
        self.output_text = QPlainTextEdit()
        self.output_text.setPlaceholderText("Improved text will appear here...")
        self.output_text.setMinimumHeight(200)
        self.output_text.setReadOnly(True)
        text_layout.addWidget(output_label)
        text_layout.addWidget(self.output_text)
        
        main_layout.addWidget(text_group)
        
        # Transform button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.transform_button = QPushButton("Transform Text")
        self.transform_button.setMinimumWidth(150)
        self.transform_button.clicked.connect(self.transform_text)
        button_layout.addWidget(self.transform_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Apply styles
        self.setStyleSheet(COMMON_STYLES)

    def transform_text(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            self.parent.window_manager.show_error.emit("Please enter some text first!")
            return
            
        try:
            style = self.style_combo.currentText()
            tone = self.tone_combo.currentText()
            model_name = self.model_combo.currentText()
            
            # Save selected options
            self.parent.settings["writing_style"] = style
            self.parent.settings["writing_tone"] = tone
            self.parent.settings["improver_model"] = SettingsWindow.AI_MODELS[model_name]
            self.parent.save_settings()
            
            # Display "Processing..." message
            self.output_text.setPlainText("Processing...")
            QApplication.processEvents()  # Update UI
            
            # Pass style and tone to academic improver
            self.parent.academic_improver.improve_text(
                text,
                style=style,
                tone=tone,
                callback=self.handle_improved_text
            )
            
        except Exception as e:
            error_msg = str(e)
            self.parent.window_manager.show_error.emit(error_msg)
            self.output_text.setPlainText("Error occurred during transformation.")

    def handle_improved_text(self, improved_text):
        """Callback function to handle the improved text from the AI"""
        self.text_ready.emit(improved_text)
    
    def update_output_text(self, text):
        """Updates the output text in the main thread"""
        self.output_text.setPlainText(text)

class SettingsWindow(QWidget):
    # Language codes as class constant
    LANGUAGES = {
        'Turkish': 'tr',
        'English': 'en',
        'German': 'de',
        'French': 'fr',
        'Spanish': 'es',
        'Italian': 'it',
        'Russian': 'ru',
        'Japanese': 'ja',
        'Korean': 'ko',
        'Chinese': 'zh-CN'
    }

    # Available keyboard shortcuts
    SHORTCUTS = [
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
        'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    ]
    
    # Function keys for Academic Improver
    FUNCTION_KEYS = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12']

    # AI Models available in OpenRouter
    AI_MODELS = {
        'DeepSeek 70B': 'deepseek/deepseek-r1-distill-llama-70b',
        'Gemini 2.0': 'google/gemini-2.0-flash-lite-001',
        'Mistral Saba': 'mistralai/mistral-saba'
    }

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setup_ui()
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon("icon.png"))
        # Daha büyük başlangıç boyutu
        self.setFixedWidth(500)  # 450'den 500'e çıkarıldı
        self.setFixedHeight(600)  # Minimum yükseklik eklendi
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)  # Kenar boşlukları artırıldı
        main_layout.setSpacing(15)  # Öğeler arası boşluk artırıldı
        
        # Header with icon and title - daha küçük
        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(QIcon("icon.png").pixmap(24, 24))
        header_layout.addWidget(icon_label)
        
        title_label = QLabel("Settings")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Tab widget ekleyerek ayarları kategorize edelim
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                background: #f8f9fa;
                padding: 8px 12px;
                border: 1px solid #bdc3c7;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: none;
            }
        """)

        # AI Assistant Tab
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        ai_layout.setContentsMargins(10, 10, 10, 10)
        ai_layout.setSpacing(12)  # Boşluk artırıldı
        
        self.use_improver = QCheckBox("Enable Academic Improver")
        self.use_improver.setChecked(self.parent.settings.get("use_improver", True))
        self.use_improver.stateChanged.connect(self.update_use_improver)
        ai_layout.addWidget(self.use_improver)

        ai_layout.addWidget(QLabel("AI Model:"))
        self.model_combo = QComboBox()
        for model_name in self.AI_MODELS.keys():
            self.model_combo.addItem(model_name)
        current_model = self.parent.settings.get("improver_model")
        current_model_name = [name for name, model in self.AI_MODELS.items() if model == current_model][0]
        self.model_combo.setCurrentText(current_model_name)
        self.model_combo.currentTextChanged.connect(self.update_model)
        ai_layout.addWidget(self.model_combo)
        
        ai_layout.addWidget(QLabel("OpenRouter API Key:"))
        self.openrouter_key_input = QLineEdit()
        self.openrouter_key_input.setText(self.parent.settings.get("openrouter_api_key", ""))
        self.openrouter_key_input.textChanged.connect(self.update_openrouter_key)
        ai_layout.addWidget(self.openrouter_key_input)
        
        ai_layout.addWidget(QLabel("Improver Shortcut:"))
        self.improve_shortcut_combo = QComboBox()
        for shortcut in self.FUNCTION_KEYS:
            self.improve_shortcut_combo.addItem(shortcut.upper())
        current_improve_shortcut = self.parent.settings.get("improve_shortcut", "f2")
        self.improve_shortcut_combo.setCurrentText(current_improve_shortcut.upper())
        self.improve_shortcut_combo.currentTextChanged.connect(self.update_improve_shortcut)
        ai_layout.addWidget(self.improve_shortcut_combo)
        
        ai_layout.addStretch()
        tabs.addTab(ai_tab, "AI Assistant")

        # Translation Tab
        trans_tab = QWidget()
        trans_layout = QVBoxLayout(trans_tab)
        trans_layout.setContentsMargins(10, 10, 10, 10)
        trans_layout.setSpacing(12)  # Boşluk artırıldı

        deepl_group = QWidget()
        deepl_layout = QHBoxLayout(deepl_group)
        self.use_deepl = QCheckBox("Use DeepL")
        self.use_deepl.setChecked(self.parent.settings["use_deepl"])
        self.use_deepl.stateChanged.connect(self.update_use_deepl)
        deepl_layout.addWidget(self.use_deepl)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("DeepL API Key")
        self.api_key_input.setText(self.parent.settings["deepl_api_key"])
        self.api_key_input.textChanged.connect(self.update_api_key)
        deepl_layout.addWidget(self.api_key_input)
        trans_layout.addWidget(deepl_group)

        shortcuts_group = QGroupBox("Translation Settings")
        shortcuts_layout = QFormLayout()
        
        self.shortcut_combo = QComboBox()
        for shortcut in self.SHORTCUTS:
            self.shortcut_combo.addItem(shortcut.upper())
        current_shortcut = self.parent.settings.get("keyboard_shortcut", "a")
        self.shortcut_combo.setCurrentText(current_shortcut.upper())
        self.shortcut_combo.currentTextChanged.connect(self.update_shortcut)
        shortcuts_layout.addRow("Shortcut Key:", self.shortcut_combo)
        
        self.lang_combo = QComboBox()
        for lang_name in self.LANGUAGES.keys():
            self.lang_combo.addItem(lang_name)
        current_lang_code = self.parent.settings["target_lang"]
        current_lang_name = [name for name, code in self.LANGUAGES.items() if code == current_lang_code][0]
        self.lang_combo.setCurrentText(current_lang_name)
        self.lang_combo.currentTextChanged.connect(self.update_target_lang)
        shortcuts_layout.addRow("Target Language:", self.lang_combo)
        
        shortcuts_group.setLayout(shortcuts_layout)
        trans_layout.addWidget(shortcuts_group)
        
        self.show_details = QCheckBox("Show detailed translation")
        self.show_details.setChecked(self.parent.settings["show_translation_details"])
        self.show_details.stateChanged.connect(self.update_show_details)
        trans_layout.addWidget(self.show_details)
        
        trans_layout.addStretch()
        tabs.addTab(trans_tab, "Translation")

        # Appearance Tab düzenlemeleri
        appear_tab = QWidget()
        appear_layout = QVBoxLayout(appear_tab)
        appear_layout.setContentsMargins(10, 10, 10, 10)
        appear_layout.setSpacing(15)

        # Font Settings Group
        font_group = QGroupBox("Font Settings")
        font_group.setMinimumHeight(120)  # Minimum yükseklik eklendi
        font_layout = QFormLayout()
        font_layout.setContentsMargins(15, 20, 15, 15)
        font_layout.setVerticalSpacing(15)
        font_layout.setHorizontalSpacing(15)
    
        self.font_combo = QFontComboBox()
        self.font_combo.setMinimumWidth(250)  # Genişlik artırıldı
        self.font_combo.setMinimumHeight(30)  # Yükseklik artırıldı
        self.font_combo.setCurrentFont(QFont(self.parent.settings["font_family"]))
        self.font_combo.currentFontChanged.connect(self.update_font)
        font_layout.addRow("Font:", self.font_combo)
        
        size_widget = QWidget()
        size_layout = QHBoxLayout(size_widget)
        size_layout.setContentsMargins(0, 0, 0, 0)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 24)
        self.size_spin.setValue(self.parent.settings["font_size"])
        self.size_spin.valueChanged.connect(self.update_font_size)
        self.size_spin.setMinimumWidth(120)  # Genişlik artırıldı
        self.size_spin.setMinimumHeight(30)  # Yükseklik artırıldı
        size_layout.addWidget(self.size_spin)
        size_layout.addStretch()
        font_layout.addRow("Size:", size_widget)
        
        font_group.setLayout(font_layout)
        appear_layout.addWidget(font_group)

        # Colors Group
        color_group = QGroupBox("Colors")
        color_group.setMinimumHeight(100)  # Minimum yükseklik eklendi
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(15, 20, 15, 15)
        color_layout.setSpacing(15)
        
        text_color_button = QPushButton("Text Color")
        text_color_button.setMinimumWidth(120)  # Genişlik artırıldı
        text_color_button.setMinimumHeight(35)  # Yükseklik artırıldı
        text_color_button.clicked.connect(self.choose_text_color)
        color_layout.addWidget(text_color_button)
        
        frame_color_button = QPushButton("Frame Color")
        frame_color_button.setMinimumWidth(120)  # Genişlik artırıldı
        frame_color_button.setMinimumHeight(35)  # Yükseklik artırıldı
        frame_color_button.clicked.connect(self.choose_frame_color)
        color_layout.addWidget(frame_color_button)
        
        color_layout.addStretch()
        color_group.setLayout(color_layout)
        appear_layout.addWidget(color_group)

        # Display Settings Group
        other_group = QGroupBox("Display Settings")
        other_group.setMinimumHeight(180)  # Yükseklik artırıldı
        other_layout = QFormLayout()
        other_layout.setContentsMargins(15, 20, 15, 15)
        other_layout.setVerticalSpacing(25)  # Dikey boşluk artırıldı
        other_layout.setHorizontalSpacing(15)
        
        transparency_widget = QWidget()
        transparency_layout = QHBoxLayout(transparency_widget)
        transparency_layout.setContentsMargins(0, 0, 0, 15)  # Alt boşluk eklendi
        self.frame_alpha_spin = QSpinBox()
        self.frame_alpha_spin.setRange(10, 100)
        self.frame_alpha_spin.setValue(int(self.parent.settings["frame_alpha"] * 100))
        self.frame_alpha_spin.valueChanged.connect(self.update_frame_alpha)
        self.frame_alpha_spin.setFixedWidth(100)
        self.frame_alpha_spin.setFixedHeight(30)
        transparency_layout.addWidget(self.frame_alpha_spin)
        transparency_layout.addStretch()
        other_layout.addRow("Frame Transparency:", transparency_widget)
        
        duration_widget = QWidget()
        duration_layout = QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        self.display_time = QSpinBox()
        self.display_time.setRange(1, 10)
        self.display_time.setValue(self.parent.settings["display_time"] // 1000)
        self.display_time.valueChanged.connect(self.update_display_time)
        self.display_time.setFixedWidth(100)
        self.display_time.setFixedHeight(30)
        duration_layout.addWidget(self.display_time)
        duration_layout.addStretch()
        other_layout.addRow("Display Duration (sec):", duration_widget)
        
        other_group.setLayout(other_layout)
        
        appear_layout.addWidget(other_group)
        
        appear_layout.addStretch()
        tabs.addTab(appear_tab, "Appearance")

        main_layout.addWidget(tabs)
        
        # Apply styles
        self.setStyleSheet(COMMON_STYLES)

    def update_target_lang(self, lang_name):
        lang_code = self.LANGUAGES[lang_name]
        self.parent.settings["target_lang"] = lang_code
        self.parent.save_settings()

    def update_show_details(self):
        self.parent.settings["show_translation_details"] = self.show_details.isChecked()
        self.parent.save_settings()

    def update_font(self):
        self.parent.settings["font_family"] = self.font_combo.currentFont().family()
        self.parent.update_label_style()
        self.parent.save_settings()

    def update_font_size(self):
        self.parent.settings["font_size"] = self.size_spin.value()
        self.parent.update_label_style()
        self.parent.save_settings()

    def choose_text_color(self):
        color = QColorDialog.getColor(
            QColor(self.parent.settings["text_color"]), 
            self,
            "Choose Text Color"
        )
        if color.isValid():
            self.parent.settings["text_color"] = color.name()
            self.parent.update_label_style()
            self.parent.save_settings()

    def choose_frame_color(self):
        color = QColorDialog.getColor(
            QColor(self.parent.settings["frame_color"]), 
            self,
            "Choose Frame Color"
        )
        if color.isValid():
            self.parent.settings["frame_color"] = color.name()
            self.parent.update_widget_style()
            self.parent.save_settings()

    def update_frame_alpha(self):
        self.parent.settings["frame_alpha"] = self.frame_alpha_spin.value() / 100
        self.parent.update_widget_style()
        self.parent.save_settings()

    def update_display_time(self):
        self.parent.settings["display_time"] = self.display_time.value() * 1000
        self.parent.save_settings()

    def update_shortcut(self, shortcut):
        self.parent.settings["keyboard_shortcut"] = shortcut.lower()
        self.parent.update_shortcut()  # Update the active shortcut
        self.parent.save_settings()

    def update_use_deepl(self):
        self.parent.settings["use_deepl"] = self.use_deepl.isChecked()
        self.parent.save_settings()
        
    def update_api_key(self):
        self.parent.settings["deepl_api_key"] = self.api_key_input.text()
        self.parent.save_settings()

    def update_openrouter_key(self):
        self.parent.settings["openrouter_api_key"] = self.openrouter_key_input.text()
        self.parent.save_settings()
        
    def update_improve_shortcut(self, shortcut):
        old_shortcut = self.parent.settings.get("improve_shortcut", "f2")
        new_shortcut = shortcut.lower()
        self.parent.settings["improve_shortcut"] = new_shortcut
        self.parent.save_settings()
        self.parent.update_shortcut()  # Update keyboard shortcuts

    def update_use_improver(self):
        self.parent.settings["use_improver"] = self.use_improver.isChecked()
        self.parent.save_settings()
        
    def update_model(self, model_name):
        self.parent.settings["improver_model"] = self.AI_MODELS[model_name]
        self.parent.save_settings()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # System tray için gerekli
    translator = TranslationWidget()
    sys.exit(app.exec())