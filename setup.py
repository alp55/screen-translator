from cx_Freeze import setup, Executable

setup(
    name="screen_translator",
    version="1.0",
    description="PySide6 ile yazılmış uygulama",
    executables=[Executable("main.py", base="Win32GUI")]
)
