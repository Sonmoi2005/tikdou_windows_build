"""
Setup file để đóng gói thành ứng dụng macOS
Chạy: python setup.py py2app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PyQt5', 'yt_dlp', 'requests', 'certifi'],
    'includes': ['PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui'],
    'excludes': ['matplotlib', 'numpy', 'pandas'],
    'plist': {
        'CFBundleName': 'TikTok Downloader',
        'CFBundleDisplayName': 'TikTok Video Downloader',
        'CFBundleIdentifier': 'com.tiktokdownloader.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025',
        'NSHighResolutionCapable': True,
    },
    'iconfile': None,  # Thêm file .icns nếu có icon
}

setup(
    name='TikTok Downloader',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    python_requires='>=3.8',
)
