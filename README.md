# Screen Translator

![Screen Translator](icon.png)

A powerful desktop application that provides real-time screen text translation and academic writing enhancement capabilities. Perfect for researchers, students, and professionals who work with multilingual content.

## ✨ Key Features

### Translation Capabilities
- 🔄 Real-time screen text translation with hotkey support (default: 'A')
- 🌍 Support for 100+ languages through Google Translate
- 🎯 DeepL API integration for professional translations
- 🔍 Automatic language detection
- ⚡ Instant floating window translation display

### Academic Writing Enhancement
- 📚 AI-powered writing improvement with multiple model options:
  - DeepSeek 70B: High-performance language model
  - Gemini 2.0: Google's advanced AI model
  - Mistral Saba: Efficient and powerful language model
- 💡 OpenRouter API integration for model access
- 🎓 Writing style customization:
  - Normal
  - Corporate
  - Academic
  - Friendly
- 📊 Tone adjustment options:
  - Enthusiastic
  - Friendly
  - Confident
  - Diplomatic

### User Interface
- 🎨 Modern Qt-based GUI with customizable themes
- 🎯 System tray integration for minimal interference
- ⚙️ Comprehensive settings panel:
  - Font customization
  - Color schemes
  - Transparency control
  - Display duration
  - Hotkey configuration
- 🖌️ Floating window with adjustable opacity

### Performance
- ⚡ Lightweight and fast translation response
- 💪 Efficient resource management
- 🔄 Background operation with system tray
- 📋 Clipboard monitoring and caching

## 🚀 Getting Started

### Prerequisites
- Windows 10/11
- Python 3.8 or higher
- pip package manager

### Required Packages
```bash
pyperclip
keyboard
deep-translator
pillow
pystray
PySide6
langdetect
pywin32>=305
pyautogui
deepl
requests
pynput
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/alp55/screen-translator.git
cd screen-translator
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

### Building Executable
```bash
python setup.py build
```

## 💻 Usage

### Basic Translation
1. Launch the application (minimizes to system tray)
2. Select any text on your screen
3. Press 'A' key (default hotkey)
4. Translation appears in a floating window

### Academic Enhancement
1. Right-click the system tray icon
2. Select "AI Writing Assistant"
3. Enter or paste your text
4. Configure settings:
   - Select AI model
   - Choose writing style
   - Set tone preference
5. Click "Transform Text"

### Configuration
Access settings through the system tray icon:
- Language preferences
- UI customization
- Hotkey configuration
- API settings
- Academic enhancement options

## ⚙️ Technical Details

### Core Components
- `main.py`: Main application and UI logic
- `academic_editor.py`: AI writing enhancement functionality
- `setup.py`: Build configuration
- `requirements.txt`: Package dependencies

### Dependencies
- PySide6: Modern Qt-based GUI framework
- deep-translator: Google Translate integration
- deepl: DeepL API support
- langdetect: Language detection
- keyboard: Global hotkey handling

## 🔑 API Configuration

### OpenRouter Setup (Required for AI Writing)
1. Create account at [OpenRouter](https://openrouter.ai/)
2. Get API key
3. Add to `settings.json`:
```json
{
  "openrouter_api_key": "your_key_here"
}
```

### DeepL Setup (Optional)
1. Get API key from [DeepL](https://www.deepl.com/pro-api)
2. Add to `settings.json`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

- GitHub: [alp55](https://github.com/alp55)
- LinkedIn: [alp55](https://linkedin.com/in/alp55)
- Email: alperen.ulutas.1@gmail.com

## 🙏 Acknowledgments

- Thanks to Google Translate and DeepL for their translation APIs
- OpenRouter for AI model access
- Icons provided by [Icons8](https://icons8.com)

---
Made with ❤️ by Alperen Ulutaş 