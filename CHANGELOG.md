# Changelog

## 0.3.0 — 2026-11-17

### Giao diện và khả năng sử dụng
- Hợp nhất các stylesheet thành `static/app.css`; thêm công cụ build/kiểm tra bằng Python tiêu chuẩn.
- Cải thiện màu sắc, typography tiếng Việt bằng font hệ thống, bảng kho, các thẻ dữ liệu, trạng thái tải và bố cục điện thoại.
- Giữ lại icon SVG, menu điện thoại, điều hướng nhanh trên desktop; thêm chỉ báo trang hiện tại.
- Cho phép mở lại trang đang xem bằng URL `?view=`; hỗ trợ Back/Forward; giảm lỗi dữ liệu trang cũ ghi đè sau khi điều hướng nhanh.
- Tìm kiếm sản phẩm có thể bỏ dấu tiếng Việt; cập nhật danh sách bán thuốc mà không mất nội dung xác minh; chặn gửi trùng đơn bán.
- Cải thiện tương tác popup với phím Escape, Tab và trả focus.

### Kiểm thử và triển khai
- Thêm kiểm tra stylesheet, kiểm thử tích hợp và GitHub Actions cho Python 3.11/3.13.
- Nâng cấp `deploy.ps1`: tải ZIP, kiểm thử trước khi thay file, sao lưu SQLite, hỗ trợ tự dừng/khởi động backend service và rollback code khi triển khai lỗi.
- Giữ nguyên SQLite schema và API endpoints.
- **Giới hạn:** Technical MVP chưa được đánh giá triển khai production; dự báo vẫn chỉ là thống kê, Copilot chưa có mô hình AI lâm sàng.

## 0.2.0 — 2026-11-17

- Rebrand Pharmora → **PharmaVision AI** with modern landing, registration and login.
- Introduce SQLite tenant boundaries, email/password signup and user roles.
- Add stock by batch, FEFO sale allocation, quarantine/recall and audit logging.
- Add dashboard, basic demand forecast, internal inventory copilot and customer history.
- Add optional Tesseract OCR and camera barcode lookup support.
- Keep previous Pharmora frontend under `legacy/`.

> Roadmap items are not implemented functionality.
