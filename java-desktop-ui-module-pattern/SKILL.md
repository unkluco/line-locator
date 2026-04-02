---
name : java-desktop-ui-module-pattern
description : Xây dựng các module UI độc lập trong Java Swing — code 1 lần, gắn được bất cứ đâu.
---

## 5 Quy tắc bắt buộc

```
QUY TẮC 1 — MODULE KHÔNG BIẾT MÌNH Ở ĐÂU
  ✅ Chỉ trả về JPanel qua getView()
  ❌ Không tự new JDialog() hay JFrame() bên trong module

QUY TẮC 2 — GIAO TIẾP DUY NHẤT QUA CALLBACK
  ✅ Dùng Consumer<Object> để trả kết quả
  ✅ Nếu user đóng cửa sổ bằng nút X → callback.accept(null)
  ✅ Nếu setOnResult(null) → module chạy độc lập, tự ẩn nút Xác nhận / Hủy
  ❌ Không gọi thẳng sang màn hình khác
  ❌ Không dùng biến static/global

QUY TẮC 3 — TỰ QUẢN LÝ STATE
  ✅ Có phương thức reset() để xóa input, về trạng thái ban đầu
  ✅ Không lưu state ra ngoài module

QUY TẮC 4 — CALLER QUYẾT ĐỊNH CÁCH HIỆN
  ✅ Dialog, Tab, Panel, ô trong lưới — do nơi gọi quyết định
  ✅ Caller tự xử lý kết quả, không để module gọi module khác
  ❌ Module không được áp đặt cách hiển thị

QUY TẮC 5 — ĐỘC LẬP HOÀN TOÀN
  ✅ Mỗi module là 1 file riêng biệt, xóa không làm hỏng gì khác
  ✅ Nhiều instance của cùng 1 module có thể tồn tại cùng lúc
  ❌ Module không được tham chiếu sang module khác
```

---

## Cấu trúc file bắt buộc

```
src/
├── modules/
│   ├── AppModule.java          ← interface quy định mọi module
│   ├── ModuleLauncher.java     ← helper hiển thị module
│   └── [TênModule]Module.java  ← từng module cụ thể
```

---

## File 1 — AppModule.java (KHÔNG SỬA)

```java
import javax.swing.JPanel;
import java.util.function.Consumer;

public interface AppModule {
    String  getTitle();                        // tên hiện trên dialog/tab
    JPanel  getView();                         // trả về giao diện
    void    setOnResult(Consumer<Object> cb);  // nhận callback
    void    reset();                           // xóa input, về ban đầu
}
```

---

## File 2 — ModuleLauncher.java (KHÔNG SỬA)

```java
import javax.swing.*;
import java.awt.*;
import java.util.function.Consumer;

public class ModuleLauncher {

    // Hiện như cửa sổ modal — bắt buộc xong mới thoát
    // Nếu user bấm X → callback nhận null
    public static void asDialog(AppModule module, JFrame parent, Consumer<Object> onResult) {
        module.reset();
        module.setOnResult(onResult);

        JDialog dialog = new JDialog(parent, module.getTitle(), true);
        dialog.setContentPane(module.getView());
        dialog.pack();
        dialog.setLocationRelativeTo(parent);

        // Bắt sự kiện bấm X — trả null về caller
        dialog.addWindowListener(new java.awt.event.WindowAdapter() {
            @Override
            public void windowClosing(java.awt.event.WindowEvent e) {
                onResult.accept(null); // 🔔 báo caller biết user đã hủy
            }
        });

        dialog.setVisible(true);
    }

    // Hiện như một tab — mỗi lần gọi tạo 1 tab mới (hỗ trợ nhiều instance)
    public static void asTab(AppModule module, JTabbedPane tabs, Consumer<Object> onResult) {
        module.reset();
        module.setOnResult(onResult);
        tabs.addTab(module.getTitle(), module.getView());
        tabs.setSelectedComponent(module.getView());
    }

    // Nhúng vào panel bất kỳ — xóa nội dung cũ rồi mới nhúng vào
    // Dùng khi ô đó chỉ hiện 1 module tại 1 thời điểm
    public static void asPanel(AppModule module, JPanel container, Consumer<Object> onResult) {
        module.reset();
        module.setOnResult(onResult);
        container.removeAll();
        container.add(module.getView(), BorderLayout.CENTER);
        container.revalidate();
        container.repaint();
    }
}
```

---

## File 3 — Template tạo module mới

> Copy file này, đổi tên class và viết lại phần BUILD UI + EXECUTE

```java
import javax.swing.*;
import java.awt.*;
import java.util.function.Consumer;

public class TênModule extends JPanel implements AppModule {

    // --- State ---
    private Consumer<Object> callback;

    // --- UI components (khai báo ở đây để reset() truy cập được) ---
    private JTextField inputField;

    // --- Constructor: chỉ gọi buildUI() ---
    public TênModule() {
        setLayout(new BorderLayout(10, 10));
        setBorder(BorderFactory.createEmptyBorder(16, 16, 16, 16));
        buildUI();
    }

    // --- UI components cho nút (field để setOnResult có thể ẩn/hiện) ---
    private JButton btnSubmit;
    private JButton btnCancel;
    private JPanel  btnPanel;

    // --- BUILD UI: thiết kế form nhập liệu ---
    private void buildUI() {
        inputField = new JTextField(20);

        btnSubmit = new JButton("Xác nhận");
        btnSubmit.addActionListener(e -> execute());

        btnCancel = new JButton("Hủy");
        btnCancel.addActionListener(e -> {
            if (callback != null) callback.accept(null); // 🔔 hủy = trả null
        });

        btnPanel = new JPanel();
        btnPanel.add(btnSubmit);
        btnPanel.add(btnCancel);

        add(inputField, BorderLayout.CENTER);
        add(btnPanel,   BorderLayout.SOUTH);
    }

    // --- EXECUTE: validate → xử lý logic → gọi callback ---
    private void execute() {
        String input = inputField.getText().trim();

        // Validate — KHÔNG gọi callback khi lỗi
        if (input.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Vui lòng nhập đầy đủ thông tin.");
            return;
        }

        Object result = input; // thay bằng logic thật (gọi service, query DB...)
        if (callback != null) callback.accept(result); // 🔔 trả kết quả về caller
    }

    // --- 4 phương thức bắt buộc của AppModule ---
    @Override public String getTitle() { return "Tên Module"; }
    @Override public JPanel getView()  { return this; }
    @Override public void setOnResult(Consumer<Object> cb) {
        this.callback = cb;
        // null = standalone mode → ẩn nút, module chạy độc lập không trả về ai
        boolean hasCallback = (cb != null);
        btnSubmit.setVisible(hasCallback);
        btnCancel.setVisible(hasCallback);
        btnPanel.setVisible(hasCallback);
    }
    @Override public void reset()      { inputField.setText(""); }
}
```

---

## Cách gọi module — 4 tình huống

### Tình huống 1: Hiện thành cửa sổ (modal)
```java
TênModule module = new TênModule();
ModuleLauncher.asDialog(module, mainFrame, result -> {
    if (result == null) return; // user hủy
    System.out.println("Kết quả: " + result);
});
```

### Tình huống 2: Hiện thành tab (nhiều tab cùng lúc được)
```java
TênModule module = new TênModule();
ModuleLauncher.asTab(module, tabbedPane, result -> {
    if (result == null) return;
    statusBar.setText("Hoàn tất: " + result);
});
```

### Tình huống 3: Nhúng vào 1 ô — thay đổi module theo hành động người dùng
```java
// Dùng asPanel — xóa nội dung cũ, nhúng module mới vào
// Ví dụ: user chọn chức năng từ menu bên trái, nội dung bên phải thay đổi
FindRouteModule findModule = new FindRouteModule();
ModuleLauncher.asPanel(findModule, contentPanel, result -> {
    if (result == null) return;
    // Mở module tiếp theo vào cùng ô đó, hoặc mở dialog
});
```

### Tình huống 4: Layout lưới / dashboard — nhiều module hiện cùng lúc
```java
// Dùng getView() trực tiếp — KHÔNG dùng asPanel vì không cần xóa gì cả
// Gắn thẳng vào từng ô khi khởi tạo màn hình

JPanel grid = new JPanel(new GridLayout(2, 2, 8, 8)); // lưới 2x2

FindRouteModule   m1 = new FindRouteModule();
BookingModule     m2 = new BookingModule();
SearchTrainModule m3 = new SearchTrainModule();
StatusModule      m4 = new StatusModule();

// Module cần trả kết quả ra ngoài → truyền callback bình thường
m1.setOnResult(result -> { if (result != null) System.out.println("Route: " + result); });
m2.setOnResult(result -> { if (result != null) System.out.println("Booked: " + result); });

// Module chỉ để thao tác, không cần trả về ai → truyền null (standalone mode)
// Nút Xác nhận / Hủy sẽ tự ẩn
m3.setOnResult(null);
m4.setOnResult(null);

grid.add(m1.getView());
grid.add(m2.getView());
grid.add(m3.getView());
grid.add(m4.getView());
```

```
┌──────────────┬──────────────┐
│ FindRoute    │ Booking      │
│   [form]     │   [form]     │
│ [OK] [Hủy]  │ [OK] [Hủy]  │  ← có callback → hiện nút
├──────────────┼──────────────┤
│ SearchTrain  │ Status       │
│   [form]     │   [form]     │
│              │              │  ← standalone → ẩn nút
└──────────────┴──────────────┘
```

---

## Khi nào dùng asPanel, khi nào dùng getView() trực tiếp

```
asPanel()          → ô chỉ hiện 1 module tại 1 thời điểm
                     module thay đổi theo hành động người dùng
                     ví dụ: khu vực nội dung chính thay đổi theo menu

getView() trực tiếp → nhiều module hiện cùng lúc ngay từ đầu
                      các ô cố định, không thay nhau
                      ví dụ: dashboard, layout lưới
```

---

## Checklist khi tạo module mới

```
□ Class extends JPanel implements AppModule
□ Có đủ 4 phương thức: getTitle, getView, setOnResult, reset
□ btnSubmit, btnCancel, btnPanel là field — không phải biến local trong buildUI()
□ setOnResult() ẩn/hiện btnPanel dựa vào cb != null
□ buildUI() chỉ tạo giao diện, KHÔNG chứa logic
□ execute() validate trước — nếu lỗi dùng JOptionPane, KHÔNG gọi callback
□ execute() thành công → if (callback != null) callback.accept(result)
□ btnCancel → if (callback != null) callback.accept(null)
□ reset() xóa hết input về trạng thái ban đầu
□ KHÔNG new JDialog/JFrame bên trong module
□ KHÔNG tham chiếu sang module khác
```

---

## Sơ đồ hoạt động

```
Caller (màn hình bất kỳ)
  │
  ├─ new TênModule()
  ├─ setOnResult(result -> { ... })        ← có callback → nút hiện
  ├─ setOnResult(null)                     ← standalone  → nút ẩn
  │
  ├─ [Dialog]  ModuleLauncher.asDialog()  ← modal, chặn tương tác
  ├─ [Tab]     ModuleLauncher.asTab()     ← thêm tab mới
  ├─ [Panel]   ModuleLauncher.asPanel()   ← thay nội dung 1 ô
  └─ [Grid]    container.add(getView())   ← nhúng thẳng vào lưới
  │
  ▼
Module hiện lên
  │
  ├─ [có callback]
  │   ├─ Bấm "Xác nhận" → execute() → callback.accept(result)   ──► Caller nhận kết quả
  │   ├─ Bấm "Hủy"      → callback.accept(null)                 ──► Caller nhận null
  │   └─ Bấm X          → windowClosing → callback.accept(null) ──► Caller nhận null
  │
  └─ [standalone — null callback]
      └─ Nút Xác nhận / Hủy bị ẩn, module tự xử lý bên trong
```

---

## Lưu ý quan trọng

- **1 module = 1 file** — không gộp nhiều module vào 1 file
- **Tên file** theo pattern: `[ChứcNăng]Module.java` — ví dụ `FindRouteModule.java`
- **Luôn kiểm tra null** trong callback trước khi dùng kết quả
- **Truyền dữ liệu giữa 2 module** → dùng constructor của module thứ 2, caller điều phối
- **Nhiều instance** — luôn `new TênModule()` mỗi lần mở, không tái dùng instance cũ
- **Layout lưới** — dùng `getView()` trực tiếp, không cần đi qua `ModuleLauncher`
