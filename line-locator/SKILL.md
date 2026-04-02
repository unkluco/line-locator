---
name : line-locator
description : Tìm các dòng của các mẫu hoặc regex nhanh trong một file, hỗ trợ biết thông tin dòng cần tìm để sau đó `view_range` chính xác và tiết kiệm token.
author  : Kluco
github  : unkluco
email   : huylet334@gmail.com
version : 1.1
---

# Line-Locator
Định vị dòng trước khi đọc file

## Tổng quan

`findtool.py` là công cụ định vị dòng trong file source code. Dùng nó để lấy **line number chính xác** trước khi gọi `view_range`, thay vì đọc mù hoặc đoán mò, tốn token.

Script nằm tại: `skills/line-locator/scripts/findtool.py`

---

## Nguyên tắc sử dụng

**Chỉ dùng findtool.py khi bạn biết chắc thứ cần tìm tồn tại trong file.**
Không cần quan tâm kích thước file hay ngôn ngữ lập trình. Nếu bạn đang tìm một hàm, một block, một keyword — và bạn biết nó ở đó — thì dùng findtool.py để định vị trước khi đọc.

**Workflow chuẩn:**
```
findtool.py (định vị) → lấy line number → view_range (đọc đúng chỗ)
```

---

## Cú pháp

```bash
python skills/line-locator/scripts/findtool.py --file PATH [OPERATION] [--json]
```

| Flag | Args | Mô tả | Output (thường) | Output (`--json`) |
|------|------|--------|-----------------|-------------------|
| `-mr` | `PAT [PAT ...]` | Tất cả dòng khớp với một hoặc nhiều regex | `a: [1,5]; b: [3]` | `{"a":[1,5],"b":[3]}` |
| `-n` | `PATTERN LINE` | Dòng đầu tiên khớp regex **sau** LINE | `45` | `45` |
| `-b` | `PATTERN LINE` | Dòng đầu tiên khớp regex **trước** LINE | `12` | `12` |
| `-c` | `OPEN LINE N` | Dòng closing delimiter khớp với OPEN thứ N trên LINE | `89` | `89` |
| `-o` | `CLOSE LINE N` | Dòng opening delimiter khớp với CLOSE thứ N trên LINE | `34` | `34` |

**Delimiters được hỗ trợ:** `{` `}` `(` `)` `[` `]`

**Lưu ý quan trọng:**
- Line number là **1-based**
- N (ordinal) là **1-based** — thứ N trên cùng một dòng
- `-n` và `-b` yêu cầu LINE **>= 1** và LINE phải tồn tại trong file
- `-n` tìm từ LINE+1, `-b` tìm từ LINE-1 — không bao gồm chính LINE
- `-c` / `-o` bỏ qua delimiter nằm trong string literal và comment — chỉ đếm delimiter "thật"
- `-mr` tự loại bỏ pattern trùng nhau, giữ thứ tự xuất hiện
- `--json` dùng được với mọi flag

---

## ⚠️ Mô hình tìm kiếm: Regex hoàn toàn

**Tất cả query đều là Python regex — không có chế độ literal riêng.**

Đây là thay đổi quan trọng nhất. Mọi pattern truyền vào `-mr`, `-n`, `-b` đều được xử lý như Python regex.

### Khi nào cần escape

Các ký tự có ý nghĩa đặc biệt trong regex: `. ( ) [ ] { } + * ? ^ $ | \`

Nếu muốn tìm các ký tự này theo nghĩa đen, phải thêm `\` trước:

```bash
# Tìm literal "foo(bar)" — ( và ) phải escape
python findtool.py --file app.py -mr "foo\(bar\)"

# Tìm literal "a.b" — dấu chấm phải escape (không escape thì khớp mọi ký tự)
python findtool.py --file app.py -mr "a\.b"

# Tên hàm thông thường không có ký tự đặc biệt — không cần escape
python findtool.py --file app.py -mr "processOrder"
python findtool.py --file app.py -mr "getUserById"
```

### Tận dụng sức mạnh regex

Vì đã là regex, có thể viết pattern mạnh hơn tìm kiếm literal nhiều:

```bash
# Tìm tất cả hàm có tên bắt đầu bằng "get" hoặc "set"
-mr "(get|set)\w+"

# Tìm khai báo hàm/method (bất kể ngôn ngữ)
-mr "\bfunction\s+\w+|def\s+\w+|void\s+\w+\s*\("

# Tìm không phân biệt hoa thường với inline flag
-mr "(?i)todo"

# Tìm dòng bắt đầu bằng import (bỏ qua comment có import)
-mr "^import\s"

# Tìm dòng khai báo class
-mr "\bclass\s+\w+"
```

---

## ⚠️ Quy tắc nền tảng: `{` có thể không cùng dòng với tên hàm

Đây là điểm dễ gây lỗi nhất. Hai phong cách tồn tại song song trong mọi ngôn ngữ:

```
# Style 1 — { cùng dòng với tên hàm
processOrder(params) {            ← dòng 247: tên hàm VÀ {

# Style 2 — { xuống dòng riêng
processOrder(params)              ← dòng 247: tên hàm
{                                 ← dòng 248: chỉ có {
```

**Không phụ thuộc vào ngôn ngữ hay convention của project** — cùng một codebase, mỗi người có thể viết khác nhau. Luôn để kết quả thực tế từ findtool.py quyết định, không đoán.

**Hệ quả áp dụng cho mọi workflow:**
- Khi cần `{` của một hàm đã biết dòng tên → dùng **`-n "{" FUNC_LINE`** để tìm OPEN_LINE thực tế
- Khi nhận được dòng chỉ chứa `{` đơn độc → tên hàm/class nằm ở **dòng trên** (`LINE - 1`)
- Khi `-c` báo lỗi `"contains only 0 valid occurrence(s)"` → `{` không ở dòng đó, dùng `-n "{" FUNC_LINE` để tìm đúng dòng

---

## ⚠️ `-n` và `-b` yêu cầu LINE >= 1 và LINE phải tồn tại trong file

```bash
# ❌ Sai — báo lỗi "LINE must be >= 1"
python findtool.py --file foo.py -n "\{" 0

# ✅ Tìm { đầu tiên trong file → dùng -mr rồi lấy phần tử đầu tiên
python findtool.py --file foo.py -mr "\{"
# → \{: [12, 25, 67, ...]  → lấy 12 làm { đầu tiên
```

---

## Workflows cơ bản

### 1. Tìm một symbol / hàm

```bash
# Tên hàm thông thường — không cần escape
python findtool.py --file app.py -mr "processOrder"
# → processOrder: [247, 312]  (247: định nghĩa, 312: call site)

# Tên hàm có ký tự đặc biệt — escape khi cần
python findtool.py --file app.py -mr "process\(Order\)"
```

---

### 2. Đọc một hàm khi đã biết tên

```bash
# Bước 1: Tìm dòng tên hàm
python findtool.py --file app.py -mr "processOrder"
# → processOrder: [247, 312]  → 247 là định nghĩa

# Bước 2: Tìm dòng { thực sự (không giả định { cùng hay khác dòng)
python findtool.py --file app.py -n "\{" 247
# → OPEN_LINE  (dùng kết quả thực tế, không đoán)

# Bước 3: Tìm dòng đóng
python findtool.py --file app.py -c "{" OPEN_LINE 1
# → 298

# Bước 4: Đọc từ dòng tên hàm đến dòng đóng
view_range [247, 298]
```

> **Tại sao `-n "\{" FUNC_LINE` thay vì `-c "{" FUNC_LINE 1` thẳng?**
> `-c` báo lỗi `"contains only 0 valid occurrence(s)"` nếu `{` không nằm trên dòng FUNC_LINE.
> `-n "\{" FUNC_LINE` luôn tìm được `{` dù nó cùng dòng hay dòng dưới.
> Nếu kết quả cách FUNC_LINE quá xa (> 2–3 dòng) → đọc thêm vài dòng đó kiểm tra — có thể là `{` của biểu thức khác.

> **Lưu ý regex cho `{`:** Khi dùng `-n` và `-b`, `{` phải viết là `\{` vì `{` là metachar trong regex. Khi dùng `-c` và `-o`, truyền nguyên ký tự `{` vì đây là delimiter matching, không phải regex.

---

### 3. Tìm nhiều symbol cùng lúc (`-mr`)

```bash
# Tìm vị trí nhiều hàm trong một lần gọi
python findtool.py --file app.py -mr "processOrder" "cancelOrder" "getOrder"
# → processOrder: [247]; cancelOrder: [312]; getOrder: [89]

# Dùng --json khi cần parse kết quả
python findtool.py --file app.py -mr "processOrder" "cancelOrder" --json
# → {"processOrder": [247], "cancelOrder": [312]}
```

> Dùng `-mr` với nhiều pattern thay vì gọi nhiều lần riêng lẻ khi cần lên kế hoạch đọc toàn bộ file. Ít tool call hơn, cùng kết quả.

---

### 4. Tìm bằng pattern mạnh

```bash
# Tìm tất cả khai báo hàm/method
python findtool.py --file service.py -mr "def \w+"
# → def \w+: [12, 45, 89, 134]

# Tìm tất cả hàm bắt đầu bằng "get" hoặc "set"
python findtool.py --file bean.py -mr "(get|set)\w+"

# Tìm tất cả TODO/FIXME không phân biệt hoa thường
python findtool.py --file app.py -mr "(?i)(todo|fixme)"

# Tìm tất cả khai báo class
python findtool.py --file app.py -mr "\bclass\s+\w+"

# Scan cấu trúc file: tìm nhiều loại khai báo cùng lúc
python findtool.py --file service.py -mr "\bclass\s+\w+" "def \w+" "^\s*#" --json
# → {"\\bclass\\s+\\w+": [1], "def \\w+": [12,45,89], "^\\s*#": [5,6]}
```

---

### 5. Đọc toàn bộ imports một lần

```bash
python findtool.py --file index.ts -mr "^import\s"
# → ^import\s: [1, 2, 3, 4, 5, 14, 15]
# min=1, max=15 → view_range [1, 15]

# Hoặc dùng pattern rộng hơn để bắt cả "require"
python findtool.py --file index.js -mr "^import\s|require\("
```

---

## Workflows nâng cao

### 6. Duyệt qua tất cả hàm trong file (khi chưa biết tên)

```bash
# Bước 1: Tìm tất cả { trong file, lấy dòng đầu tiên
python findtool.py --file foo.py -mr "\{"
# → \{: [12, 25, 67, 89, ...]  → OPEN_LINE đầu tiên = 12

# Bước 2: Đọc dòng 12 và dòng trên để biết tên
# - Nếu dòng 12 có tên hàm + {  → tên là dòng 12
# - Nếu dòng 12 chỉ có {        → tên là dòng 11
view_range [11, 12]

# Bước 3: Nhảy qua toàn bộ body hàm hiện tại
python findtool.py --file foo.py -c "{" 12 1
# → 67  (dòng đóng)

# Bước 4: Tìm { tiếp theo sau dòng đóng
python findtool.py --file foo.py -n "\{" 67
# → 70  → đọc dòng 69–70 để biết tên hàm tiếp theo

# Lặp lại bước 3–4 cho đến hết file
```

> **Duyệt hàm bên trong một block:** Nếu `{` ở dòng 12 là mở class/namespace, dùng `-n "\{" 12` để tìm block đầu tiên bên trong nó thay vì nhảy ra ngoài.

> **Lọc khai báo hàm khi duyệt:** `-mr "\{"` trả về tất cả `{` gồm cả if/for/while. Để lọc chỉ hàm, dùng thêm `-mr "def \w+|\bfunction\s+\w+|void\s+\w+"` để có danh sách dòng tham chiếu trước khi duyệt.

---

### 7. Xác định dòng đang thuộc scope nào

Khi đang ở dòng X và không biết nó thuộc hàm/block gì:

```bash
# Tìm { mở gần nhất phía trên dòng X
python findtool.py --file dao.py -b "\{" X
# → 134  (dòng chứa {)

# Xác nhận X nằm trong scope đó
python findtool.py --file dao.py -c "{" 134 1
# → 189  (nếu 189 > X thì X đúng là trong scope này)

# Đọc tên hàm/block:
# - Nếu dòng 134 có tên hàm + {  → đọc dòng 134
# - Nếu dòng 134 chỉ có {        → tên hàm ở dòng 133
view_range [133, 135]
```

---

### 8. Tìm cặp {} bao bọc trực tiếp một dòng hoặc đoạn

Khi biết dòng X (hoặc đoạn X–Y) và muốn biết `{...}` trực tiếp bao quanh nó:

```bash
# Tìm { gần nhất phía trên X
python findtool.py --file app.py -b "\{" X
# → OPEN_LINE

# Tìm } gần nhất phía dưới X
python findtool.py --file app.py -n "\}" X
# → CLOSE_LINE

# Kiểm tra chúng có phải là cặp hợp lệ không
python findtool.py --file app.py -c "{" OPEN_LINE 1
# → Nếu kết quả == CLOSE_LINE thì đây đúng là cặp bao trực tiếp
```

---

### 9. Leo scope chain — tìm context ngoài cùng

Khi code lồng sâu, muốn biết block ở tầng ngoài cùng bao chứa một dòng:

```bash
# Lặp -b "\{" nhiều lần để leo từng tầng scope
python findtool.py --file app.py -b "\{" 245  →  198  # { tầng trong cùng
python findtool.py --file app.py -b "\{" 198  →  134  # { tầng kế
python findtool.py --file app.py -b "\{" 134  →  12   # { tầng ngoài
python findtool.py --file app.py -b "\{" 12   →  Error → dừng, đây là top-level

# Với mỗi dòng { tìm được, đọc dòng đó VÀ dòng trên để xác định tên scope
view_range [11, 13]
```

---

### 10. Đọc argument list / parameter dài nhiều dòng

```bash
# Tìm ) đóng tương ứng với ( mở ở dòng LINE
python findtool.py --file builder.py -c "(" LINE 1
# → CLOSE_LINE

view_range [LINE, CLOSE_LINE]
```

---

### 11. Tìm else / catch / finally tương ứng

```bash
# Tìm dòng đóng { của block if ở IF_LINE
python findtool.py --file handler.py -c "{" IF_LINE 1
# → 78

# Tìm else/catch ngay sau đó
python findtool.py --file handler.py -n "else|catch|finally" 78
# → 79  (nếu kết quả gần ngay sau 78 thì đây là else/catch của block đó)
```

> Regex cho phép tìm `else|catch|finally` trong một lần thay vì tìm từng cái riêng.

---

### 12. Phát hiện decorator / annotation trước khi đọc hàm

```bash
# Kiểm tra có annotation không trước khi view_range hàm ở FUNC_LINE
python findtool.py --file routes.py -b "@\w+" FUNC_LINE
# → Nếu kết quả >= FUNC_LINE - 3 → có decorator trực tiếp → mở rộng range lên
# → Nếu kết quả < FUNC_LINE - 3  → không có decorator ngay trên hàm, bỏ qua

view_range [DECORATOR_LINE, CLOSE_LINE]
```

> **Lưu ý:** `-b` luôn trả về một kết quả nào đó (decorator gần nhất trong toàn file), không phải chỉ decorator ngay phía trên hàm. Dùng ngưỡng `>= FUNC_LINE - 3` để phân biệt decorator trực tiếp với decorator của hàm khác bên trên.

> Pattern `@\w+` khớp decorator/annotation ở nhiều ngôn ngữ khác nhau mà không cần biết tên cụ thể.

---

### 13. Scan nhanh cấu trúc tổng thể của file

```bash
# Lấy vị trí tất cả khai báo quan trọng trong một lần
python findtool.py --file service.py -mr "\bclass\s+\w+" "def \w+" "^\s*(//|#)\s*MARK" --json
# → {"\bclass\s+\w+": [1], "def \\w+": [12,45,89,134], ...}
# Dùng kết quả này để lên kế hoạch đọc, không cần view toàn bộ file
```

---

## Bảng quyết định nhanh

| Tình huống | Dùng gì |
|---|---|
| Biết tên hàm, muốn đọc body | `-mr "tenHam"` → `-n "\{" FUNC_LINE` → `-c "{"` |
| Cần vị trí nhiều hàm cùng lúc | `-mr "fn1" "fn2" "fn3"` |
| Tìm theo pattern (get/set, public, class...) | `-mr "pattern_regex"` |
| Tìm `{` đầu tiên trong file | `-mr "\{"` → lấy `result[0]` |
| Duyệt từng hàm không biết tên | `-mr "\{"` → `result[0]` → `-c "{"` → `-n "\{"` → lặp |
| Đang ở dòng X, muốn biết thuộc hàm nào | `-b "\{"` → đọc dòng đó + dòng trên → `-c "{"` verify |
| Muốn đọc hết imports | `-mr "^import\s"` → min/max |
| Argument list dài nhiều dòng | `-c "("` |
| Tìm else/catch/finally | `-c "{"` rồi `-n "else\|catch\|finally"` |
| Có decorator/annotation không? | `-b "@\w+"` |
| Đang ở code lồng sâu, tìm block ngoài cùng | `-b "\{"` lặp, mỗi bước đọc dòng đó + dòng trên |
| Cần parse kết quả trong script | thêm `--json` vào bất kỳ lệnh nào |

---

## Bảng escape ký tự hay gặp

Áp dụng cho `-mr`, `-n`, `-b`. **Không áp dụng cho `-c` và `-o`** (delimiter matching, không phải regex).

| Muốn tìm | Viết pattern | Ghi chú |
|---|---|---|
| `{` | `\{` | Hay dùng trong `-n "\{" LINE` |
| `}` | `\}` | Hay dùng trong `-b "\}" LINE` |
| `(` | `\(` | |
| `)` | `\)` | |
| `[` | `\[` | |
| `.` | `\.` | Dấu chấm không escape = khớp mọi ký tự |
| `foo(bar)` | `foo\(bar\)` | Tên hàm có tham số literal |
| `a.b` | `a\.b` | |
| Bất kỳ `{` hoặc `}` | `[{}]` | Dùng character class |
| Tên hàm thông thường | `processOrder` | Không có ký tự đặc biệt → không cần escape |

---

## Xử lý lỗi thường gặp

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `"LINE must be >= 1"` | Truyền `0` vào `-n` hoặc `-b` | Dùng `-mr "\{"` rồi lấy `result[0]` thay vì `-n "\{" 0` |
| `"LINE must be between 1 and N"` | LINE vượt quá số dòng thực tế của file | Kiểm tra lại line number |
| `"contains only 0 valid occurrence(s) of '{'"` | `{` không nằm trên dòng đó | Dùng `-n "\{" FUNC_LINE` để tìm dòng `{` thực tế |
| `"does not have a valid matching"` | Delimiter không có cặp hợp lệ | File có thể có syntax lỗi, hoặc delimiter trong string/comment bị bỏ qua đúng thiết kế |
| `"No line matching regex ... was found"` | Pattern không khớp trong phạm vi tìm | Kiểm tra lại regex, hoặc mở rộng phạm vi |
| `"Invalid regex pattern"` | Regex sai cú pháp | Kiểm tra lại pattern — hay gặp khi quên escape `(`, `)`, `{` |

---

## Ví dụ thực tế end-to-end

**Bài toán:** Đọc hàm `validateToken` trong `AuthService` (file 800 dòng), bao gồm cả annotation.

```bash
# 1. Định vị dòng tên hàm
python findtool.py --file AuthService.py -mr "validateToken"
# → validateToken: [312, 467]  (312: định nghĩa, 467: call site)

# 2. Kiểm tra có annotation/decorator không
python findtool.py --file AuthService.py -b "@\w+" 312
# → 310  (có decorator ở dòng 310)

# 3. Tìm dòng { thực sự của hàm (không giả định cùng dòng hay khác dòng)
python findtool.py --file AuthService.py -n "\{" 312
# → 313  (kết quả thực tế — dùng con số này, không đoán)

# 4. Tìm dòng đóng
python findtool.py --file AuthService.py -c "{" 313 1
# → 389

# 5. Đọc từ decorator đến dòng đóng
view_range [310, 389]
```

**Tổng token tiêu thụ:** ~80 dòng thay vì 800 dòng. Tiết kiệm ~90%.

---

## Lưu ý cuối

- `-mr` với một pattern duy nhất = thay thế cho tìm kiếm đơn giản cũ.
- `-mr` với nhiều patterns = thay thế cho nhiều lần tìm riêng lẻ — dùng khi cần lên kế hoạch đọc.
- `{` trong `-c`/`-o` viết nguyên ký tự. `{` trong `-n`/`-b`/`-mr` phải viết `\{`.
- Kết hợp `--json` khi cần xử lý output trong script hoặc parse nhiều kết quả:
  ```bash
  python findtool.py --file app.py -mr "\bclass\s+\w+" "def \w+" --json
  ```