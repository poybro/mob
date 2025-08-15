# Nội dung hoàn chỉnh cho file buildozer.spec
buildozer_spec_content = """
[app]
# (Bắt buộc) Tiêu đề, tên gói và miền
title = SOK Chain Wallet
package.name = sokwallet
package.domain = org.sokchain.wallet

# (Bắt buộc) Thư mục chứa mã nguồn (để là . nếu main.py ở thư mục gốc)
source.dir = .

# (Bắt buộc) Các phần mở rộng tệp cần đóng gói
source.include_exts = py,png,jpg,kv,atlas,ttf,json

# (Bắt buộc) Phiên bản ứng dụng
version = 0.1

# (QUAN TRỌNG) Các thư viện Python cần thiết
# cryptography là một recipe phức tạp, cần các thư viện hệ thống
requirements = python3,kivy,requests,cryptography,qrcode,pillow

# (Bắt buộc) Quyền truy cập Internet cho requests
android.permissions = INTERNET

# (Tùy chọn) Cấu hình màn hình và biểu tượng
orientation = portrait
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/logo.png

# (QUAN TRỌNG) Thêm các thư viện hệ thống cần thiết cho Cryptography
# openssl và ffi là bắt buộc cho recipe cryptography
android.recipe_dependencies = openssl,host_openssl,libffi

# (Tùy chọn) Tăng phiên bản Android API để tương thích tốt hơn
android.api = 31
android.minapi = 21
android.sdk = 24
android.ndk = 25b

# (Tối ưu) Các kiến trúc cần build. arm64-v8a là bắt buộc trên Google Play
android.archs = arm64-v8a

[buildozer]
# (Bắt buộc) Mức độ log chi tiết để dễ gỡ lỗi
log_level = 2

# (FIX CHO COLAB) Tắt cảnh báo chạy với quyền root để tránh bị hỏi
warn_on_root = 0
"""

# Ghi nội dung trên vào file buildozer.spec
with open('buildozer.spec', 'w') as f:
    f.write(buildozer_spec_content)

print("Tệp 'buildozer.spec' đã được tạo/cập nhật thành công!")
