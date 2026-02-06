# Comic Vault

Desktop app (Python + PySide6) để lưu trữ và quản lý danh sách truyện bạn đang đọc: lưu URL, chương hiện tại, ghi chú, ảnh bìa, rating, mở nhanh truyện trên trình duyệt.

---

## Tính năng

### Library
- Hiển thị truyện dạng **card grid**
- **Search** theo title/source/status
- Hover card có các nút:
  - **Open**: mở truyện bằng trình duyệt
  - **Edit**: mở màn hình Add/Edit với dữ liệu đã được điền sẵn
  - **Delete**: xoá truyện

### Add / Edit
- Form riêng để thêm/sửa truyện
- Field chính:
  - Title, Source, URL
  - Status (reading/paused/completed/dropped)
  - Rating (0 = None)
  - Current Chapter, Current URL
  - Notes
  - Cover Image (chọn ảnh + preview)
- Hỗ trợ nhanh:
  - **Paste URL** từ clipboard
  - **Open URL** bằng trình duyệt
  - **Fetch Title** bằng QtWebEngine (browser-like) + fallback khi bị chặn (nếu đã bật)

---

## Tech Stack

- Python 3.11+ (khuyến nghị)
- UI: **PySide6**
- WebEngine: **PySide6-Addons** (QtWebEngine)
- DB: **SQLite**
- ORM: **SQLModel**

---

## Cài đặt & Chạy

### 1. Tạo môi trường ảo (venv)
**Windows (PowerShell)**
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

**macOS/Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Cài dependencies
```bash
pip install -U pip
pip install PySide6 PySide6-Addons sqlmodel
```

### 3. Chạy app
```bash
python -m comic_vault.main
```

## Cấu trúc thư mục (tham khảo)
```css
comic_vault/
  main.py
  data/
    db.py
    models.py
    comic_vault.db
  ui/
    theme.py
    main_window.py
    pages/
      library_page.py
      editor_page.py
    widgets/
      flow_layout.py
      comic_card.py
    utils/
      web_title.py
      title_browser.py   # (nếu bạn dùng fallback interactive browser)
```