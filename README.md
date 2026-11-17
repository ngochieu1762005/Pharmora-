# PharmaVision AI

**Nền tảng quản trị và hỗ trợ ra quyết định thông minh cho nhà thuốc**

Phiên bản: **0.2.0 — Local MVP** · Giao diện tiếng Việt · Python + SQLite + HTML/CSS/JavaScript

> **Quan trọng:** Đây là phiên bản MVP để trình diễn và phát triển sản phẩm. Không dùng với thông tin bệnh nhân thật, không phải hệ thống nhà thuốc đã được chứng nhận GPP, không kết nối trực tiếp với Bộ Y tế và **chưa cung cấp AI lâm sàng**. Mọi thông tin về thuốc, đơn kê, cảnh báo thu hồi cần được dược sĩ kiểm tra bằng nguồn có thẩm quyền.

## Bắt đầu nhanh — Windows

Cài **Python 3.10+** (khuyến nghị 3.11/3.12/3.13). Giải nén ZIP, mở CMD trong thư mục `PharmaVision-AI` và chạy:

```bat
py server.py
```

Hoặc nhấp đúp `run.bat`. Mở trình duyệt tại **http://127.0.0.1:8000**.

1. Trên trang giới thiệu, chọn **Bắt đầu miễn phí**.
2. Nhập **tên nhà thuốc, họ tên, email và mật khẩu tối thiểu 10 ký tự**.
3. Bật **dữ liệu mẫu** nếu muốn thấy ngay các sản phẩm và lô minh họa.
4. Nhấp **Tạo workspace**. Bạn sẽ tự động đăng nhập vào dashboard và có quyền quản trị viên trong nhà thuốc vừa tạo.
5. Tạo tài khoản nhân viên tại **Cài đặt & tài khoản**.

**Không có tài khoản hoặc mật khẩu mặc định.** Không cần đăng nhập bằng ChatGPT, không cần OpenAI key, không cần Node.js, không cần cài package Python cho chức năng cơ bản.

Linux/macOS:

```bash
python3 server.py
# hoặc ./run.sh
```

Truy cập:

| URL | Nội dung |
| --- | --- |
| `/` | Trang giới thiệu giải pháp (landing page) |
| `/register` | Đăng ký nhà thuốc, tạo workspace |
| `/login` | Đăng nhập bằng email/mật khẩu |
| `/app` | Workspace quản lý nhà thuốc |

Để chạy ở cổng khác: `py server.py --port 8080`.

**Quên mật khẩu:** người có quyền quản lý máy chủ có thể dừng server và chạy:

```bat
py server.py --reset-email admin@example.com
```

Đổi `admin@example.com` thành email của tài khoản cần khôi phục. Chương trình sẽ hỏi mật khẩu mới bằng cách nhập ẩn; mọi phiên cũ bị thu hồi.

## Tính năng đang hoạt động

| Nhóm | Đã triển khai trong bản MVP |
| --- | --- |
| Website giới thiệu | Hero, giới thiệu 2 giải pháp, tính năng, quy trình, bảo mật, FAQ, CTA đăng ký; responsive desktop/mobile |
| Tài khoản | Đăng ký công khai, mật khẩu băm bằng scrypt, phiên đăng nhập cookie HttpOnly, CSRF token, đổi mật khẩu, tạo nhân viên, vai trò admin/staff |
| Đa nhà thuốc | Mỗi tài khoản thuộc một workspace riêng; API lọc dữ liệu bằng `pharmacy_id` phía server, có bài kiểm thử cách ly dữ liệu |
| Smart Inventory | Thêm danh mục, hoạt chất, hàm lượng, dạng bào chế, Rx, barcode, giá, ngưỡng tồn; nhập lô và nhà cung cấp; xem tồn theo lô và HSD; kiểm kê có nhật ký |
| Xuất bán | Giỏ hàng, chọn khách, FEFO theo hạn dùng, chống xuất âm và chặn lô hết hạn/cách ly; giao dịch SQLite atomic; bắt buộc người phụ trách xác nhận; thuốc Rx yêu cầu tích xác nhận và mã đơn *do người dùng cung cấp* |
| Cảnh báo | Sắp hết hạn, tồn thấp, lô cách ly; quản trị viên nhập thông báo thu hồi nội bộ và tự động cách ly các lô trùng khớp |
| Barcode | Nhập bằng USB/manual; thử quét camera nếu trình duyệt có hỗ trợ `BarcodeDetector` |
| OCR | API nhận diện văn bản tiếng Việt/Anh qua **Tesseract cài tại máy chủ** (tùy chọn), gợi ý số lô/ngày, **không tự động ghi kho** |
| Forecast | Phương pháp minh bạch: trung bình bán 30 ngày, thời gian giao hàng và đệm tồn kho; không tự nhận là mô hình ML |
| Pharmacist Copilot | Tra cứu danh mục thuốc, hoạt chất, lô, số lượng có thể bán và trạng thái cách ly **từ DB nội bộ** |
| Smart Customer Profile | Tên, liên hệ, cờ đồng ý, ghi chú sức khỏe tự khai nếu đã đồng ý; xem lịch sử đơn mua và mã đơn; quản trị viên xóa hồ sơ |
| Theo dõi | Dashboard KPI dựa trên dữ liệu đã ghi, lịch sử bán, nhật ký thao tác, xuất CSV danh mục |

## Những tính năng **chưa triển khai**

- **AI chuyên sâu:** chưa có mô hình ML dự báo đa biến có mùa vụ/dịch tễ hoặc mô hình thực tế đã hiệu chỉnh; hiện chỉ có baseline thống kê.
- **Dữ liệu thuốc và tương tác:** chưa có bộ dữ liệu lâm sàng được thẩm định, không xác nhận tương tác, liều dùng, chống chỉ định và thay thế thuốc.
- **Hệ thống CSDL về dược Bộ Y tế và đơn thuốc điện tử:** chưa được cấp quyền kết nối/kiểm thử, không xác minh mã đơn, chưa có gửi dữ liệu liên thông.
- **Tự động lấy cảnh báo thu hồi:** bản này chỉ có thao tác nhập thủ công từ nguồn được xác minh.
- **Zalo OA:** chưa gửi thông báo/hướng dẫn hoặc nhắc lịch.
- **Chuỗi nhà thuốc nhiều chi nhánh:** hiện có nhiều workspace độc lập, chưa có vận hành đa chi nhánh trong một pháp nhân.
- **SaaS production:** chưa có HTTPS proxy, chống bot toàn diện, mã hóa dữ liệu sức khỏe ở tầng ứng dụng, kiểm thử xâm nhập, chu trình xóa/lưu trữ theo luật, backup vận hành, SSO/OAuth, quản lý tác vụ nền, billing.
- **OCR chuẩn hóa danh mục:** văn bản được trích xuất, nhưng tên thuốc, hàm lượng, lô và hạn dùng vẫn phải được người dùng xác nhận và nhập chính xác.

## OCR trên Windows (tùy chọn)

1. Cài **Tesseract OCR** cho Windows (bản phân phối đáng tin cậy).
2. Cài đặt traineddata `vie` và `eng` (nếu có) để xử lý tiếng Việt/Anh.
3. Đảm bảo lệnh `tesseract --version` chạy được trong CMD (thêm đường dẫn cài vào `PATH`).
4. Khởi động lại `py server.py`, mở **Smart Inventory → Nhập bằng ảnh OCR**, chọn ảnh PNG/JPEG/WEBP tối đa 3MB.
5. Đối chiếu lại số lô/hạn sử dụng với chứng từ gốc. Sau đó nhập kho thủ công.

**Lưu ý:** Trình duyệt camera thường cần `localhost` hoặc HTTPS và `BarcodeDetector` chưa có trên mọi trình duyệt. Máy quét mã vạch USB có thể nhập vào trường barcode bình thường.

## Bảo mật và kiến trúc

- Python `http.server` **chỉ dùng cục bộ**. Mặc định chỉ lắng nghe `127.0.0.1`.
- Mật khẩu được băm **scrypt có salt**; cookie session `HttpOnly`, `SameSite=Lax`, hết hạn 12 giờ. Đặt `PHARMAVISION_SECURE_COOKIE=1` **chỉ khi** phục vụ qua HTTPS.
- Mọi API thay đổi dữ liệu (ngoại trừ đăng ký/đăng nhập) yêu cầu session và **CSRF token**.
- Quyền quản trị được kiểm tra phía máy chủ (thêm nhân viên, kiểm kê, cách ly, thu hồi, xóa hồ sơ).
- `pharmacy_id` được lấy từ session trên server; không tin giá trị tenant truyền từ client.
- Mọi đơn bán được cập nhật tồn trong transaction có khóa ghi `BEGIN IMMEDIATE`, thứ tự lô theo `expires` tăng dần.
- Hành động quan trọng có dòng `audit`; **không phải immutable ledger**.
- Dữ liệu nằm trong `pharmavision.sqlite3` (tự tạo). **Không đưa file này lên Git.** Để thay đường dẫn DB: `PHARMAVISION_DB=/path/to/db.sqlite3`.
- Không tích hợp OpenAI hoặc ChatGPT; chatbot tra cứu chạy bằng quy tắc truy vấn cơ sở dữ liệu.

## Kiểm thử

```bat
py -m unittest -v test_app.py
```

Bộ kiểm thử kiểm tra đăng ký/đăng nhập, CSRF, phân quyền, cách ly nhiều nhà thuốc, nhập/xuất FEFO, chống xuất vượt tồn, thu hồi/cách ly, yêu cầu Rx, ràng buộc sự đồng ý và các trang frontend.

## Cấu trúc mã nguồn

```text
PharmaVision-AI/
├─ server.py                 # HTTP/API, SQLite, auth, kho, khách hàng, forecast, OCR
├─ static/
│  ├─ index.html             # Website giới thiệu
│  ├─ login.html             # Đăng nhập
│  ├─ register.html          # Đăng ký nhà thuốc
│  ├─ workspace.html         # Dashboard / shell
│  ├─ styles.css             # Design system responsive
│  ├─ site.js                # Landing + xác thực
│  └─ workspace.js           # UI quản trị và API calls
├─ legacy/                   # Bản giao diện Pharmora cũ để đối chiếu (không chạy)
├─ test_app.py               # Kiểm thử API
├─ docs/ARCHITECTURE.md      # Kiến trúc và quy trình dữ liệu
├─ docs/ROADMAP.md           # Mô-đun tiếp theo
├─ run.bat / run.sh          # Khởi động nhanh
└─ .gitignore
```

## Tài liệu pháp lý để định hướng phát triển

Những văn bản dưới đây là **tài liệu tham chiếu và yêu cầu cần đánh giá**, không đồng nghĩa hệ thống đã đạt chứng nhận hay đã liên thông:

- [Thông tư 11/2025/TT-BYT của Bộ Y tế](https://dav.gov.vn/images/upload_file/2025/thong-tu-11_2025_tt_bytsigned_1747821215.pdf): cập nhật quy định quản lý cơ sở bán lẻ thuốc và yêu cầu dữ liệu.
- [Quyết định 522/QĐ-TTYQG (18/12/2025), tài liệu đặc tả API CSDL về dược](https://www.nhic.vn/cong-bo-tai-lieu-ky-thuat-dac-ta-api-he-thong-co-so-du-lieu-ve-duoc/): kiến trúc tích hợp cần xây ở giai đoạn triển khai được cấp quyền.
- [Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15](https://vanban.chinhphu.vn/?docid=214590&pageid=27160), hiệu lực 01/01/2026: cần đánh giá phạm vi, mục đích, sự đồng ý, bảo vệ và vòng đời dữ liệu.

## Nâng cấp từ source Pharmora trước đó

Bản này là **thiết kế lại thành đa nhà thuốc**, không ghi đè trực tiếp schema SQLite/JSON phiên bản Pharmora cũ. Giao diện cũ được lưu trong `legacy/` để tham khảo. Nếu có dữ liệu thực cần chuyển, phải viết và kiểm thử quy trình migration riêng; **không** copy file `pharmora.sqlite3` vào project mới.

**Không triển khai công khai trên Internet hoặc dùng để điều hành nhà thuốc thật khi chưa qua đánh giá kỹ thuật, an toàn thông tin, quy trình dược và pháp lý.**
