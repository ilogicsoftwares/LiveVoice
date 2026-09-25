"""Make bundled CUDA runtime libraries visible to CTranslate2 on Windows."""

import os
import sys

if sys.platform == "win32" and getattr(sys, "frozen", False):
    _cuda_dll_directory = os.add_dll_directory(sys._MEIPASS)
    os.environ["PATH"] = sys._MEIPASS + os.pathsep + os.environ.get("PATH", "")
