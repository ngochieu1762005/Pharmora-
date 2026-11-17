# Triển khai PharmaVision AI trên Windows Server (VPS)

> Tài liệu dành cho **demo kỹ thuật với dữ liệu giả**, không phải hướng dẫn vận hành nhà thuốc thật. Phiên bản 0.2.x dùng Python `http.server` + SQLite, chưa được đánh giá bảo mật và tuân thủ để phục vụ dữ liệu sức khỏe thực. Không mở cổng 8000 ra Internet; giữ quyền đăng ký/ghi dữ liệu trong phạm vi thử nghiệm tin cậy.

## Thông tin mẫu của dự án

- Repository: https://github.com/ngochieu1762005/Pharmora-
- VPS Windows: `103.77.172.235` (thay IP khi chuyển nhà cung cấp)
- Domain: `pharmavision.hieuds.com`
- App: `C:\web\pharmora`, Python: `C:\Program Files\Python313\python.exe`
- Caddy: `C:\caddy\caddy.exe`; Python chỉ nghe `127.0.0.1:8000`

## Lần đầu thiết lập

Từ PowerShell **trên máy cá nhân**:

```powershell
ssh Administrator@103.77.172.235
```

Máy VPS SSH Windows có thể mở CMD, hãy gõ `powershell` trước khi chạy cmdlet như `New-Item`. Đảm bảo Python 3.10+ đã cài. Nếu chưa cài Git, tải ZIP từ GitHub:

```powershell
New-Item -ItemType Directory -Force C:\web\pharmora | Out-Null
Invoke-WebRequest "https://github.com/ngochieu1762005/Pharmora-/archive/refs/heads/main.zip" -OutFile C:\web\main.zip
Expand-Archive C:\web\main.zip C:\web\source -Force
$src = Get-ChildItem C:\web\source -Directory | Select-Object -First 1
Copy-Item "$($src.FullName)\*" C:\web\pharmora -Recurse -Force
cd C:\web\pharmora
& "C:\Program Files\Python313\python.exe" -m unittest -v test_app.py
$env:PHARMAVISION_SECURE_COOKIE="1"
& "C:\Program Files\Python313\python.exe" server.py
```

Kiểm tra cục bộ bằng SSH tunnel trước khi mở web:

```powershell
# Chạy trên máy cá nhân trong terminal thứ hai
ssh -L 8000:127.0.0.1:8000 Administrator@103.77.172.235
# Mở http://localhost:8000
```

## DNS và Caddy (HTTPS)

Cloudflare → DNS tạo A `pharmavision` → `103.77.172.235`. Khi bật **Proxied**, DNS công khai trả về IP Cloudflare là bình thường. Cần mở TCP 80/443 trên firewall VPS **và** firewall nhà cung cấp, kiểm tra từ máy cá nhân; lệnh `Test-NetConnection` tự chạy ngay trên VPS không chứng minh kết nối bên ngoài.

Cài Caddy từ https://caddyserver.com/download (Windows AMD64) vào `C:\caddy`. Đảm bảo cổng 80/443 không bị IIS/HTTP.sys chiếm; kiểm tra trước khi dừng dịch vụ.

```powershell
# Chạy trên VPS PowerShell Admin; chỉ mở nếu chưa có rule tương ứng
New-NetFirewallRule -DisplayName "Pharmora HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "Pharmora HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
Get-NetTCPConnection -LocalPort 80,443 -State Listen -ErrorAction SilentlyContinue
```

Để người truy cập tới thẳng trang chủ và dùng form đăng nhập của ứng dụng, cấu hình **Caddyfile**:

```caddyfile
pharmavision.hieuds.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
```

> Không có `basic_auth` nghĩa là **mọi người có thể truy cập landing page và trang đăng ký demo**. Chỉ gỡ lớp bảo vệ ngoài trên môi trường dữ liệu giả được chấp thuận; nếu cần bảo vệ, cấu hình `basic_auth` theo hướng dẫn Caddy.

```powershell
@'
pharmavision.hieuds.com {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
'@ | Set-Content C:\caddy\Caddyfile -Encoding ascii
C:\caddy\caddy.exe validate --config C:\caddy\Caddyfile
C:\caddy\caddy.exe run --config C:\caddy\Caddyfile
```

Caddy tự quản lý HTTPS. Nếu chứng chỉ ACME bị lỗi khi Cloudflare Proxied, **tạm** chuyển hostname sang DNS only và kiểm tra từ Internet 80/443, chờ Caddy cấp chứng chỉ; sau đó bật lại Proxy và dùng Full (strict) khi chứng chỉ origin hợp lệ. Đừng đổi SSL mode của toàn bộ zone nếu website khác có origin chưa phù hợp.

## Khi push code mới lên GitHub

**Cách an toàn cho VPS chưa cài Git:** Đảm bảo bạn đã đẩy code lên `main`; trên VPS chạy PowerShell Admin. Trước khi cập nhật, dừng Python đang chạy bằng `Ctrl+C` trong terminal chứa `server.py` (đừng tắt Caddy). Sau đó:

```powershell
cd C:\web\pharmora
# Script đi kèm source hiện tại, khi nâng cấp lần đầu có thể tải bản mới từ GitHub:
Invoke-WebRequest "https://raw.githubusercontent.com/ngochieu1762005/Pharmora-/main/deploy.ps1" -OutFile C:\web\deploy.ps1
& C:\web\deploy.ps1
```

Script `deploy.ps1` tải ZIP, chạy unittest **trước** khi ghi đè, tạo backup `C:\web\backups\<timestamp>` và bảo toàn `pharmavision.sqlite3`, `.env`, `uploads`. Nếu app đang chạy, script sẽ yêu cầu dừng trước. Không tự sửa migration schema SQLite; trước khi đổi schema cần thiết kế migration có kiểm thử.

Khởi chạy Python trong phiên SSH:

```powershell
cd C:\web\pharmora
$env:PHARMAVISION_SECURE_COOKIE="1"
& "C:\Program Files\Python313\python.exe" server.py
```

Caddy chỉ cần `reload` khi **Caddyfile** đổi:

```powershell
C:\caddy\caddy.exe validate --config C:\caddy\Caddyfile
C:\caddy\caddy.exe reload --config C:\caddy\Caddyfile
```

Kiểm tra trên VPS:

```powershell
curl.exe -sS -o NUL -w "Python HTTP: %{http_code}`n" http://127.0.0.1:8000/
curl.exe -k -o NUL -w "Local proxy HTTP: %{http_code}`n" --resolve pharmavision.hieuds.com:443:127.0.0.1 https://pharmavision.hieuds.com/
```

Kiểm tra **ngoài VPS, không dùng `-k`**:

```powershell
curl.exe -I https://pharmavision.hieuds.com
```

Nếu frontend vẫn cũ, tải cứng trang `Ctrl+Shift+R`. Nếu code Python thay đổi, **phải khởi động lại Python**; Caddy không tự nạp code Python. Bản demo chạy từ terminal sẽ dừng khi phiên điều khiển kết thúc. Muốn 24/7: thiết lập service manager Windows phù hợp cho **cả Caddy và Python** với tài khoản có quyền tối thiểu và quy trình backup; không cấu hình `sc.exe` trực tiếp cho Python vì `server.py` không implement Windows Service API.

### Chẩn đoán nhanh

| Biểu hiện | Nơi kiểm tra |
| --- | --- |
| `502` | Python còn nghe ở `127.0.0.1:8000` không |
| `401` | Caddy `basic_auth` vẫn bật, hoặc credentials sai |
| `522` | Cloudflare không tới được VPS; kiểm tra firewall, IIS, cổng 80/443 từ ngoài |
| `525/526` | TLS/SSL giữa Cloudflare và origin, kiểm tra chứng chỉ và SSL mode |
| `bind 127.0.0.1:2019` | Đã có tiến trình Caddy; kiểm tra trước khi chạy thêm |
| `New-Item is not recognized` | SSH đang dùng CMD, gõ `powershell` |
| `py is not recognized` | Python chưa cài/chưa vào PATH; dùng đường dẫn đầy đủ |

## Checklist sau mỗi lần deploy

- [ ] Unit tests pass trên mã nguồn mới
- [ ] SQLite được backup và không bị ghi đè
- [ ] Python chạy trên `127.0.0.1:8000`
- [ ] HTTPS public hợp lệ **không cần** `-k`
- [ ] Đăng nhập/đăng ký và thử điều hướng ở viewport 360 / 390 / 768 / desktop
- [ ] Thử kho, bán thuốc, giỏ hàng, modal và menu điện thoại
- [ ] Chỉ dùng dữ liệu giả; không nhập thông tin bệnh nhân thật
