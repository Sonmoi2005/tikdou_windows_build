#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok/Douyin → Facebook Reels Downloader - GUI Version
- Giao diện đồ họa PyQt5
- GIỮ NGUYÊN độ dài video
- Ưu tiên video ngắn trong N video mới nhất
"""

import sys
import os
import re
import time
import subprocess
import json
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout,
        QHBoxLayout, QPushButton, QLineEdit, QLabel,
        QTableWidget, QTableWidgetItem, QFileDialog,
        QSpinBox, QMessageBox, QProgressBar, QHeaderView,
        QDialog, QCheckBox
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
except ImportError:
    print("❌ Cần cài PyQt5: pip3 install PyQt5")
    print("⚠️  Nếu dùng Python 3.14, khuyên dùng Python 3.12")
    sys.exit(1)

try:
    import yt_dlp
except ImportError:
    print("❌ Cần cài yt-dlp: pip3 install yt-dlp")
    sys.exit(1)


def sanitize_filename(text, max_length=100):
    """Làm sạch chuỗi để dùng làm tên file.

    Lưu ý: Trả về '' nếu rỗng để tránh tạo đuôi '_untitled' như trước.
    """
    if not text:
        return ""
    text = re.sub(r'[<>:"/\\|?*]', '', str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_length] if len(text) > max_length else text

def extract_video_id(url: str) -> str:
    """Trích xuất ID video (nếu có) từ URL TikTok/Douyin."""
    if not url:
        return ""
    u = str(url)
    m = re.search(r"/video/(\d+)", u)
    if m:
        return m.group(1)
    # Fallback: chuỗi số dài (thường là id)
    m = re.search(r"(\d{10,})", u)
    return m.group(1) if m else ""

def _is_url(text: str) -> bool:
    return bool(re.match(r'^https?://', (text or '').strip(), re.IGNORECASE))


def detect_platform(text: str) -> str:
    """Trả về 'tiktok' hoặc 'douyin' dựa trên input."""
    t = (text or '').lower()
    if "douyin.com" in t or "iesdouyin.com" in t or "v.douyin.com" in t:
        return "douyin"
    if "tiktok.com" in t:
        return "tiktok"
    return "tiktok"  # mặc định giữ tương thích cũ


def normalize_channel_input(raw: str):
    """Chuẩn hóa input thành (platform, url).

    - TikTok: cho phép nhập username hoặc URL.
    - Douyin: khuyến nghị nhập URL kênh/video; hỗ trợ thêm:
      + 'douyin:<sec_uid_or_url>'
      + sec_uid bắt đầu bằng 'MS4w...' (thường gặp)
    """
    raw = (raw or "").strip()
    if not raw:
        return "tiktok", ""

    if _is_url(raw):
        return detect_platform(raw), raw

    low = raw.lower()
    if low.startswith("douyin:"):
        rest = raw.split(":", 1)[1].strip()
        if _is_url(rest):
            return "douyin", rest
        rest = rest.lstrip("@")
        return "douyin", f"https://www.douyin.com/user/{rest}"

    # Douyin sec_uid thường bắt đầu bằng MS4w...
    if raw.startswith("MS4w"):
        return "douyin", f"https://www.douyin.com/user/{raw}"

    # TikTok username (giữ tương thích cũ)
    username = raw.lstrip("@").strip()
    return "tiktok", f"https://www.tiktok.com/@{username}"



def _looks_like_tiktok_username(s: str) -> bool:
    if not s:
        return False
    s = s.strip()
    if s.startswith("@"):
        s = s[1:]
    return bool(re.fullmatch(r"[A-Za-z0-9._]{2,64}", s))


def derive_profile_url_from_video_info(info: dict, platform: str, fallback_url: str = "") -> str:
    """Cố gắng suy ra URL kênh từ info của 1 video (TikTok/Douyin).

    Trả về chuỗi URL (https://...) hoặc '' nếu không suy ra được.
    """
    if not isinstance(info, dict):
        return ""

    # 1) Ưu tiên các trường URL nếu yt-dlp đã cung cấp
    for k in ("uploader_url", "channel_url", "creator_url", "uploader_webpage_url", "webpage_url_basename"):
        v = info.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v

    # 2) TikTok: thường có uploader_id ~ username
    if platform == "tiktok":
        cand = info.get("uploader_id") or info.get("creator") or info.get("uploader")
        if isinstance(cand, str):
            cand = cand.strip()
            if cand.startswith("@"):
                cand = cand[1:]
            if _looks_like_tiktok_username(cand):
                return f"https://www.tiktok.com/@{cand}"

    # 3) Douyin: thường dùng sec_uid (hay gặp dạng MS4w...)
    if platform == "douyin":
        cand = info.get("uploader_id") or info.get("channel_id") or info.get("uploader")
        if isinstance(cand, str):
            cand = cand.strip()
            # sec_uid thường dài và có thể bắt đầu bằng MS4w..., nhưng cũng có dạng khác
            if cand and not cand.startswith("http") and len(cand) >= 10:
                return f"https://www.douyin.com/user/{cand}"

    # 4) Fallback heuristic: nếu URL video chứa @username (TikTok)
    if platform == "tiktok" and isinstance(fallback_url, str):
        m = re.search(r"tiktok\.com/@([^/]+)/video/", fallback_url)
        if m:
            return f"https://www.tiktok.com/@{m.group(1)}"

    return ""

class VideoInfo:
    def __init__(self, url, title, description, hashtags):
        self.url = url
        self.title = title
        self.description = description
        self.hashtags = hashtags
        self.status = "Chờ"
        self.duration = 0

    def get_filename(self):
        caption = sanitize_filename(self.description or self.title, 80)
        # Nếu caption rỗng, dùng ID video để tránh file tên trống
        if not caption:
            vid = extract_video_id(self.url)
            caption = f"video_{vid}" if vid else f"video_{int(time.time())}"

        hashtag_str = "_".join(self.hashtags[:3]) if self.hashtags else ""
        hashtag_str = sanitize_filename(hashtag_str, 30)

        if hashtag_str:
            return f"{caption}_{hashtag_str}.mp4"
        return f"{caption}.mp4"


class ScanProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đang quét kênh")
        self.setModal(True)
        self.setFixedSize(400, 180)

        layout = QVBoxLayout(self)
        self.info_label = QLabel("Đang lấy danh sách video...")
        layout.addWidget(self.info_label)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.detail_label = QLabel("0/0 video (0%)")
        layout.addWidget(self.detail_label)

        btn_layout = QHBoxLayout()
        self.action_btn = QPushButton("Dừng quét")
        self.action_btn.clicked.connect(self.on_action_clicked)
        btn_layout.addWidget(self.action_btn)
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.stop_requested = False
        self.cancel_requested = False
        self.is_paused = False

    def on_action_clicked(self):
        if not self.is_paused:
            self.stop_requested = True
            self.is_paused = True
            self.action_btn.setText("Tiếp tục")
            self.cancel_btn.setEnabled(True)
            if hasattr(self, 'stop_callback'):
                self.stop_callback()
        else:
            self.stop_requested = False
            self.is_paused = False
            self.action_btn.setText("Dừng quét")
            self.cancel_btn.setEnabled(False)
            if hasattr(self, 'resume_callback'):
                self.resume_callback()

    def on_cancel_clicked(self):
        self.cancel_requested = True
        if hasattr(self, 'cancel_callback'):
            self.cancel_callback()
        self.close()

    def update_progress(self, current, total, percent):
        self.progress_bar.setValue(percent)
        self.detail_label.setText(f"{current}/{total} video ({percent}%)")


class ScanThread(QThread):
    fetching_signal = pyqtSignal()
    total_found_signal = pyqtSignal(int)
    progress_signal = pyqtSignal(int, int, int)
    video_added_signal = pyqtSignal(object)
    finished_signal = pyqtSignal(bool, bool)
    error_signal = pyqtSignal(str)

    def __init__(self, url, start_index=0, entries=None, cookie_file=""):
        super().__init__()
        self.url = url
        self.start_index = start_index
        self.entries = entries
        self.cookie_file = cookie_file or ""
        self.stop_requested = False
        self.cancel_requested = False

    def run(self):
        try:
            if self.entries is None:
                self.fetching_signal.emit()
                platform, target_url = normalize_channel_input(self.url)
                if not target_url:
                    self.entries = []
                else:
                    ydl_opts = {
                        'quiet': True,
                        'extract_flat': True,
                        'playlistend': 10000,
                        'ignoreerrors': True
                    }

                    # Douyin thường cần header/cookies để quét/tải ổn định hơn
                    if platform == "douyin":
                        # Dùng User-Agent của Windows để tránh bị Douyin chặn
                        ydl_opts['http_headers'] = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
                            'Referer': 'https://www.douyin.com/'
                        }
                        if self.cookie_file and os.path.exists(self.cookie_file):
                            ydl_opts['cookiefile'] = self.cookie_file

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(target_url, download=False)

                    # Nếu là kênh thì thường có 'entries'.
                    if info and isinstance(info, dict) and info.get("entries"):
                        self.entries = [e for e in info.get("entries", []) if e]
                    elif info and isinstance(info, dict):
                        # Input là link 1 video -> cố suy ra URL kênh để quét toàn bộ kênh
                        profile_url = derive_profile_url_from_video_info(info, platform, target_url)
                        if profile_url and profile_url != target_url:
                            try:
                                info2 = ydl.extract_info(profile_url, download=False)
                            except Exception:
                                info2 = None

                            if info2 and isinstance(info2, dict) and info2.get("entries"):
                                self.entries = [e for e in info2.get("entries", []) if e]
                            else:
                                self.entries = [info]
                        else:
                            self.entries = [info]
                    elif info:
                        self.entries = [info]
                    else:
                        self.entries = []

            total = len(self.entries)
            self.total_found_signal.emit(total)
            if total == 0:
                self.finished_signal.emit(False, False)
                return

            time.sleep(0.3)

            for idx in range(self.start_index, total):
                if self.cancel_requested or self.stop_requested:
                    self.finished_signal.emit(False, self.cancel_requested)
                    return

                entry = self.entries[idx]
                if not entry:
                    continue

                video = VideoInfo(
                    entry.get("url", "") or entry.get("webpage_url", ""),
                    entry.get("title", ""),
                    entry.get("description", entry.get("title", "")),
                    re.findall(r"#(\w+)", entry.get("description", "") or "")
                )
                video.duration = entry.get("duration", 0)
                self.video_added_signal.emit(video)
                self.progress_signal.emit(idx + 1, total, int((idx + 1) / total * 100))
                time.sleep(0.002)

            self.finished_signal.emit(True, False)
        except Exception as e:
            self.error_signal.emit(str(e))

    def stop(self):
        self.stop_requested = True

    def cancel(self):
        self.cancel_requested = True
        self.stop_requested = True


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int, str, str)
    finished_signal = pyqtSignal()

    def __init__(self, videos, save_dir, cookie_file=""):
        super().__init__()
        self.videos = videos
        self.save_dir = save_dir
        self.cookie_file = cookie_file or ""
        self.is_paused = False
        self.is_stopped = False
        self.current_index = 0
        self.has_ffmpeg = self.check_ffmpeg()

    def check_ffmpeg(self):
        """Check for ffmpeg availability.

        Khi chạy dưới dạng file .exe trên Windows, cố gắng tìm ffmpeg.exe nằm cùng thư mục
        hoặc bên trong thư mục con `ffmpeg\bin`. Nếu không tìm thấy, thử dùng ffmpeg trong PATH.
        Lưu đường dẫn ffmpeg vào self.ffmpeg_path nếu tìm thấy.
        """
        # Mặc định không có ffmpeg
        self.ffmpeg_path = ''
        # Nếu đang chạy từ PyInstaller (.exe), thử tìm ffmpeg cạnh .exe
        if getattr(sys, 'frozen', False):
            exe_dir = Path(sys.executable).resolve().parent
            local_candidates = [exe_dir / 'ffmpeg.exe', exe_dir / 'ffmpeg' / 'bin' / 'ffmpeg.exe']
            for p in local_candidates:
                if p.exists():
                    self.ffmpeg_path = str(p)
                    return True
        # Fallback: dùng ffmpeg trong PATH
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            self.ffmpeg_path = 'ffmpeg'
            return True
        except Exception:
            return False

    def run(self):
        for i, video in enumerate(self.videos):
            if self.is_stopped:
                break
            while self.is_paused:
                time.sleep(0.5)

            self.current_index = i
            dur_text = f"{int(video.duration)}s" if video.duration > 0 else "?s"
            self.progress_signal.emit(i, "Downloading", f"Tải {i+1}/{len(self.videos)} ({dur_text})")

            if self.download_video(video, i):
                self.progress_signal.emit(i, "Done", "✓ OK")
            else:
                self.progress_signal.emit(i, "Failed", "✗ Lỗi")

        self.finished_signal.emit()

    def download_video(self, video, index):
        temp = f"temp_{index}_{int(time.time())}.mp4"
        
        try:
            # Tải video
            ydl_opts = {
                'outtmpl': temp,
                'format': 'best',
                'quiet': True,
                'concurrent_fragment_downloads': 5
            }

            # Douyin: thêm headers/cookies nếu có để tránh lỗi 403/verify
            platform = detect_platform(video.url)
            if platform == "douyin":
                # Dùng User-Agent của Windows để tránh bị Douyin chặn
                ydl_opts['http_headers'] = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
                    'Referer': 'https://www.douyin.com/'
                }
                if self.cookie_file and os.path.exists(self.cookie_file):
                    ydl_opts['cookiefile'] = self.cookie_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video.url])
            
            # Tạo filename
            filename = video.get_filename()
            filepath = os.path.join(self.save_dir, filename)
            counter = 1
            while os.path.exists(filepath):
                name, ext = os.path.splitext(filename)
                filepath = os.path.join(self.save_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            # Encode
            if self.has_ffmpeg:
                self.progress_signal.emit(index, "Encoding", "⚡ Encode...")
                self.encode_video(temp, filepath)
            else:
                os.rename(temp, filepath)
            
            if os.path.exists(temp):
                os.remove(temp)
            return True
        except Exception as e:
            print(f"[ERROR] {e}")
            if os.path.exists(temp):
                os.remove(temp)
            return False

    def encode_video(self, input_path, output_path):
        """Encode video - GIỮ NGUYÊN độ dài"""
        ffmpeg_cmd = self.ffmpeg_path or 'ffmpeg'
        cmd = [
            ffmpeg_cmd, '-i', input_path,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-maxrate', '5M', '-bufsize', '10M',
            '-profile:v', 'baseline', '-level', '3.1', '-threads', '0',
            '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-ac', '2',
            '-map_metadata', '-1', '-map_metadata:s:v', '-1', '-map_metadata:s:a', '-1',
            '-movflags', '+faststart', '-pix_fmt', 'yuv420p',
            '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
            '-y', output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=600)

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_stopped = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.videos = []
        self.download_thread = None
        # Mặc định lưu vào Downloads/TikTok (trên Windows sẽ sinh ra đường dẫn phù hợp)
        self.save_dir = str(Path.home() / "Downloads" / "TikTok")

        # Cookies Douyin (tuỳ chọn):
        # Khi chạy từ PyInstaller (.exe), __file__ không khả dụng. Thay vào đó dùng sys.executable để
        # xác định thư mục chứa file .exe. Nếu chạy script bình thường, dùng __file__.
        if getattr(sys, 'frozen', False):
            # PyInstaller đặt sys.executable tại đường dẫn của .exe
            tool_dir = Path(sys.executable).resolve().parent
        else:
            tool_dir = Path(__file__).resolve().parent

        cand1 = tool_dir / "cookies_douyin.txt"
        cand2 = tool_dir / "cookies.txt"
        self.cookie_file = str(cand1) if cand1.exists() else (str(cand2) if cand2.exists() else "")

        self.scan_thread = None
        self.scan_entries = None
        self.scan_dialog = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("TikTok/Douyin → Facebook Reels [GIỮ NGUYÊN độ dài]")
        self.setGeometry(100, 100, 1100, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Input
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Nhập username TikTok (vd: ciaramakeup2003) hoặc URL kênh/video Douyin")
        input_layout.addWidget(QLabel("Kênh:"))
        input_layout.addWidget(self.url_input)
        self.scan_btn = QPushButton("Quét kênh")
        self.scan_btn.clicked.connect(self.start_scanning)
        input_layout.addWidget(self.scan_btn)
        layout.addLayout(input_layout)

        # Info
        info_layout = QHBoxLayout()
        self.video_count_label = QLabel("Số video: 0")
        info_layout.addWidget(self.video_count_label)
        info_layout.addWidget(QLabel("Số video tải:"))
        self.video_limit_spin = QSpinBox()
        self.video_limit_spin.setRange(1, 10000)
        self.video_limit_spin.setValue(10)
        self.video_limit_spin.valueChanged.connect(self.update_table)
        info_layout.addWidget(self.video_limit_spin)
        self.prioritize_checkbox = QCheckBox("Ưu tiên ≤60s")
        self.prioritize_checkbox.setChecked(True)
        self.prioritize_checkbox.stateChanged.connect(self.update_table)
        info_layout.addWidget(self.prioritize_checkbox)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Folder
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel(f"Thư mục: {self.save_dir}")
        folder_layout.addWidget(self.folder_label)
        self.folder_btn = QPushButton("Chọn thư mục")
        self.folder_btn.clicked.connect(self.choose_folder)
        folder_layout.addWidget(self.folder_btn)
        layout.addLayout(folder_layout)

        # Cookies Douyin (tuỳ chọn)
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(QLabel("Cookies Douyin:"))
        self.cookie_path_edit = QLineEdit()
        self.cookie_path_edit.setReadOnly(True)
        self.cookie_path_edit.setText(self.cookie_file)
        cookie_layout.addWidget(self.cookie_path_edit)
        self.cookie_btn = QPushButton("Chọn cookies")
        self.cookie_btn.clicked.connect(self.choose_cookie_file)
        cookie_layout.addWidget(self.cookie_btn)
        self.cookie_clear_btn = QPushButton("Xóa")
        self.cookie_clear_btn.clicked.connect(self.clear_cookie_file)
        cookie_layout.addWidget(self.cookie_clear_btn)
        layout.addLayout(cookie_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["STT", "Tên file", "Trạng thái", "Duration"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Controls
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("Bắt đầu tải")
        self.start_btn.clicked.connect(self.start_download)
        self.start_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        self.pause_btn = QPushButton("Tạm dừng")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        control_layout.addWidget(self.pause_btn)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.statusBar().showMessage("✅ Hỗ trợ TikTok + Douyin - GIỮ NGUYÊN độ dài - Ưu tiên video ngắn")

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục", self.save_dir)
        if folder:
            self.save_dir = folder
            self.folder_label.setText(f"Thư mục: {self.save_dir}")

    def choose_cookie_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file cookies (cookies.txt)",
            str(Path.home()),
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.cookie_file = path
            self.cookie_path_edit.setText(path)

    def clear_cookie_file(self):
        self.cookie_file = ""
        self.cookie_path_edit.setText("")

    def start_scanning(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập username hoặc URL")
            return
        
        self.videos = []
        self.table.setRowCount(0)
        self.scan_dialog = ScanProgressDialog(self)
        self.scan_dialog.stop_callback = lambda: self.scan_thread.stop() if self.scan_thread else None
        self.scan_dialog.cancel_callback = lambda: self.scan_thread.cancel() if self.scan_thread else None
        self.scan_dialog.show()

        self.scan_thread = ScanThread(url, cookie_file=self.cookie_file)
        self.scan_thread.fetching_signal.connect(lambda: self.scan_dialog.info_label.setText("Đang lấy danh sách..."))
        self.scan_thread.total_found_signal.connect(lambda t: self.video_count_label.setText(f"Số video: {t}"))
        self.scan_thread.progress_signal.connect(lambda c, t, p: self.scan_dialog.update_progress(c, t, p))
        self.scan_thread.video_added_signal.connect(self.on_video_added)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.start()

    def on_video_added(self, video):
        self.videos.append(video)
        self.update_table()

    def on_scan_finished(self, success, cancelled):
        if self.scan_dialog and success:
            self.scan_dialog.close()
        if self.videos:
            self.start_btn.setEnabled(True)

    def update_table(self):
        if not self.videos:
            return
        
        limit = min(self.video_limit_spin.value(), len(self.videos))
        selected = self.videos[:limit]
        
        if self.prioritize_checkbox.isChecked():
            selected = sorted(selected, key=lambda v: (
                0 if 0 < v.duration <= 60 else 1, 
                v.duration if v.duration > 0 else 9999
            ))
        
        self.table.setRowCount(len(selected))
        for i, video in enumerate(selected):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(video.get_filename()))
            self.table.setItem(i, 2, QTableWidgetItem("Chờ"))
            
            dur = f"{int(video.duration)}s" if video.duration > 0 else "?"
            if 0 < video.duration <= 60:
                dur = f"⚡{dur}"
            elif video.duration > 60:
                dur = f"🐢{dur}"
            self.table.setItem(i, 3, QTableWidgetItem(dur))
        
        self.videos_to_download = selected

    def start_download(self):
        if not hasattr(self, 'videos_to_download'):
            return
        
        os.makedirs(self.save_dir, exist_ok=True)
        self.download_thread = DownloadThread(self.videos_to_download, self.save_dir, cookie_file=self.cookie_file)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.start()
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)

    def toggle_pause(self):
        if self.download_thread:
            if self.download_thread.is_paused:
                self.download_thread.resume()
                self.pause_btn.setText("Tạm dừng")
            else:
                self.download_thread.pause()
                self.pause_btn.setText("Tiếp tục")

    def update_progress(self, index, status, message):
        self.table.setItem(index, 2, QTableWidgetItem(status))
        self.progress_bar.setValue(int((index + 1) / self.table.rowCount() * 100))
        self.table.scrollToItem(self.table.item(index, 0))

    def download_finished(self):
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "Hoàn thành", "✅ Đã tải xong tất cả video!")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
