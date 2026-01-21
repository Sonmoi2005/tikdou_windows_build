# TikTok Video Downloader - No Watermark

Công cụ tải video TikTok không watermark, chạy trên macOS với giao diện đồ họa.

## Tính năng

✅ Quét toàn bộ video trên kênh TikTok  
✅ Chọn số lượng video cần tải  
✅ Tên file = Caption + Hashtag  
✅ Chọn thư mục lưu  
✅ Hiển thị trạng thái từng video  
✅ Video chất lượng cao, không watermark  
✅ Nút Tạm dừng / Tiếp tục tải  
✅ Tải tuần tự từng video, không tạo file .part  
✅ Tối ưu cho lượng video lớn  

## Cài đặt

### Bước 1: Cài đặt Python 3.8+

Kiểm tra Python:
```bash
python3 --version
```

Nếu chưa có, tải tại: https://www.python.org/downloads/

### Bước 2: Cài đặt thư viện

```bash
pip3 install -r requirements.txt
```

## Sử dụng

### Cách 1: Chạy trực tiếp (qua Terminal)

```bash
python3 main.py
```

### Cách 2: Đóng gói thành ứng dụng .app

#### A. Cài đặt py2app:
```bash
pip3 install py2app
```

#### B. Build ứng dụng:
```bash
python3 setup.py py2app
```

#### C. Ứng dụng sẽ có trong thư mục `dist/`:
```
dist/TikTok Downloader.app
```

Kéo file này vào thư mục Applications hoặc double-click để chạy.

### Cách 3: Dùng Automator ( đơn giản hơn)

1. Mở **Automator** (tìm trong Spotlight)
2. Chọn **New Document** → **Application**
3. Tìm action "Run Shell Script" và kéo vào
4. Dán code sau:

```bash
#!/bin/bash
cd /đường/đấn/đến/thư/mục/chứa/main.py
/usr/local/bin/python3 main.py
```

(Thay `/đường/đấn/đến/thư/mục/chứa/main.py` bằng đường dẫn thật)

5. **File** → **Save** → Đặt tên: "TikTok Downloader"
6. Lưu vào Desktop hoặc Applications
7. Double-click để chạy!

## Hướng dẫn sử dụng tool

1. **Nhập link kênh**: Nhập username (vd: `@username`) hoặc URL đầy đủ
2. **Click "Quét kên kề kê̇nh"**: Tool sẽ liệt kê̇ tẫ lất tất cả video
3. **Chọn số video**: Nhập số video muốn tải (mặc định 10)
4. **Chọn thư mục**: Click "Chọn thư mục" để chọn nơi lưu
5. **Click "Bắt đầu tải"**: Tool sẻ tải tuần tự từng video
6. **Tạm dừng/Tiếp tục**: Dùng nút "Tạm dừng" khi cần

## Lưu ý

⚠️ **Bản quyền**: Tool này chỉ để sử dụng cá nhân. Tôn trọng bản quyền nội dung.  
⚠️ **TikTok API**: Tool sử dụng yt-dlp, có thể gặp giới hạn khi tải quá nhiều video liên tục.  
⚠️ **Kết nối mạng**: Đảm bảo kết nối internet ổn định khi tải.  

## Xử lý lỗi thường gặp

### Lỗi: "No module named PyQt5"
```bash
pip3 install PyQt5
```

### Lỗi: "yt-dlp not found"
```bash
pip3 install yt-dlp
```

### Lỗi: Không quét được video
- Kiểm tra link kên TikTok có đúng không
- Kên có thể bị private hoặc không tồn tại
- Thử cập nhật yt-dlp: `pip3 install -U yt-dlp`

### Lỗi khi build .app
```bash
# Xóa cache và build lại
rm -rf build dist
python3 setup.py py2app
```

## Tối ưu hiệu suất

- **RAM**: Nên có ít nhất 4GB RAM khi tải nhiều video
- **Disk**: Đảm bảo đủ dung lượng ổ cứng (video HD có thể 20-100MB/video)
- **Mạng**: Tốc độ internet càng nhanh, tải càng nhanh
- **Số video**: Với hàng nghìn video, nên tải theo tỷ lô 100-200 video

## Version

- **Version**: 1.0.0
- **Ngày**: 02/12/2025
- **Hỗ trợ**: macOS 10.14+

## Liên hệ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra file log (nếu có)
2. Thử chạy `python3 main.py` qua Terminal để xem lỗi chi tiết
3. Cập nhật các thư viện: `pip3 install -U -r requirements.txt`

---

**Lưu ý quan trọng**: Tool này được phát triển cho mục đích học tập và sử dụng cá nhân. 
Người dùng có trách nhiệm tuân thủ điều khoản sử dụng của TikTok và luật bản quyền.
