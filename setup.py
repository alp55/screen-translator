from cx_Freeze import setup, Executable

setup(
    name="screen_translator",
    version="1.0",
    description="Screen Translator",
    executables=[Executable("main.py", base="Win32GUI")]
)
