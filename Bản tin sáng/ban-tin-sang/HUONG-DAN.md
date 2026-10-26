# Bản tin sáng: hướng dẫn đưa app lên iPhone

App chạy như một web app cài lên Màn hình chính (PWA). Dùng được trên iPhone 12 trở đi, với điều kiện máy đã cập nhật iOS 16.4 trở lên (cần cho thông báo đẩy). Tất cả dịch vụ bên dưới đều có gói miễn phí.

## Bộ file này gồm gì

| Đường dẫn | Việc của nó |
|---|---|
| `public/index.html` | Giao diện app, đọc tin từ `digest.json` |
| `public/digest.json` | Bản tin. Hiện là tin mẫu, sẽ được ghi đè mỗi sáng |
| `public/manifest.webmanifest`, `public/*.png` | Để iPhone nhận đây là một app (tên, biểu tượng) |
| `public/OneSignalSDKWorker.js` | Cho phép nhận thông báo đẩy |
| `scripts/build_digest.py` | Lấy tin từ RSS các báo, loại tin trùng, xếp hạng, gửi thông báo |
| `.github/workflows/ban-tin.yml` | Lịch chạy tự động: 6:30 sáng lấy tin, 20:00 tối nhắc đọc |

## Bước 1. Đưa mã lên GitHub

1. Tạo tài khoản tại github.com (nếu chưa có), chọn **New repository**, đặt tên `ban-tin-sang`.
2. Giải nén file zip, rồi kéo thả toàn bộ thư mục vào repo (chọn **uploading an existing file**).
   Lưu ý: thư mục ẩn `.github` phải được tải lên. Nếu máy không cho kéo thả thư mục ẩn, hãy dùng GitHub Desktop hoặc lệnh `git`.

## Bước 2. Đưa app lên mạng bằng Cloudflare Pages

1. Đăng ký tại dash.cloudflare.com, vào **Workers & Pages**, chọn **Create**, rồi **Pages**, rồi **Connect to Git**.
2. Chọn repo `ban-tin-sang`. Để trống **Build command**. Ở **Build output directory** nhập `public`. Bấm **Save and Deploy**.
3. Sau ít phút bạn có địa chỉ dạng `https://ban-tin-sang.pages.dev`. Đây là địa chỉ app của bạn.

Mỗi khi bot ghi bản tin mới vào repo, Cloudflare tự đăng lại trang.

## Bước 3. Bật thông báo bằng OneSignal

1. Đăng ký tại onesignal.com, tạo một app mới, chọn nền tảng **Web**, kiểu **Typical site**.
2. Điền địa chỉ trang ở Bước 2. Với các mục về Safari trên iPhone, làm theo gợi ý trong trang cấu hình của OneSignal (giao diện của họ có thể đổi theo thời gian).
3. File service worker `OneSignalSDKWorker.js` đã có sẵn trong `public/`, bạn không cần tải thêm.
4. Lấy hai giá trị trong **Settings, Keys & IDs**: **App ID** và **REST API Key**.
5. Mở `public/index.html` trên GitHub, tìm dòng `var ONESIGNAL_APP_ID="DAN_APP_ID_ONESIGNAL_VAO_DAY";` và thay bằng App ID của bạn, rồi lưu (commit).

## Bước 4. Cho bot quyền gửi thông báo

Trong repo GitHub: **Settings, Secrets and variables, Actions, New repository secret**. Tạo các khóa sau:

| Tên | Giá trị |
|---|---|
| `ONESIGNAL_APP_ID` | App ID ở Bước 3 |
| `ONESIGNAL_REST_KEY` | REST API Key ở Bước 3 |
| `SITE_URL` | Địa chỉ trang ở Bước 2 |
| `ANTHROPIC_API_KEY` | Không bắt buộc. Nếu có, tin tiếng Anh được dịch và tóm tắt sang tiếng Việt bằng Claude. Có phát sinh phí nhỏ theo lượng dùng |

Vào tab **Actions**, chọn **ban-tin**, rồi **Run workflow** để chạy thử. Xem nhật ký: dòng `OK` là nguồn lấy được, dòng `LỖI` là nguồn cần sửa địa chỉ RSS trong `scripts/build_digest.py`.

## Bước 5. Cài lên iPhone

1. Mở **Safari** trên iPhone, vào địa chỉ trang ở Bước 2.
2. Bấm nút **Chia sẻ**, chọn **Thêm vào Màn hình chính**, rồi **Thêm**.
3. Mở app từ biểu tượng mới trên Màn hình chính (không mở trong Safari).
4. Bấm **Bật thông báo** và chọn **Cho phép**.

Từ đó, 6:30 sáng bạn nhận bản tin, và 20:00 tối nhận lời nhắc nếu quên.

## Tùy chỉnh

- Đổi giờ gửi: sửa hai dòng `cron` trong `.github/workflows/ban-tin.yml`. Giờ trong đó tính theo UTC (giờ Việt Nam trừ 7 tiếng).
- Thêm hoặc bớt báo: sửa danh sách `FEEDS` trong `scripts/build_digest.py`.
- Số tin mỗi mục: sửa `LIMITS` trong cùng file.

## Những điều cần biết

- Bản tin chỉ hiện tiêu đề, một đoạn tóm tắt ngắn và đường dẫn về bài gốc. Đừng sửa app để chép toàn văn bài báo, vì sẽ vướng bản quyền.
- Lịch của GitHub Actions có thể trễ vài phút đến vài chục phút vào giờ cao điểm.
- Địa chỉ RSS của các báo thỉnh thoảng thay đổi. Nếu một nguồn báo `LỖI`, hãy tìm địa chỉ RSS mới trên trang của báo đó.
- Mình chưa thể chạy thử việc lấy RSS thật và gửi thông báo trong môi trường tạo file này (không có mạng), nên lần chạy đầu có thể cần chỉnh nhỏ theo nhật ký.
