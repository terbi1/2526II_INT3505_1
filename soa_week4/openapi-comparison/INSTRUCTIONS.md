---

## 1. Câu hỏi

> **Nên sử dụng format nào cho để document API?**

Repo này không có câu trả lời duy nhất đúng — mà trình bày 4 cách tiếp cận khác nhau, mỗi cách document **cùng một API thực tế**, để bạn tự so sánh và đưa ra quyết định phù hợp với ngữ cảnh của mình.

---

## 2. API dùng để minh họa

Tất cả 4 format đều document **cùng một API**: `Book Management API`, một Flask app nhỏ nằm trong `app.py` ở root repo.

---

## 3. Tiêu chí so sánh

Mỗi format được xem xét trên 6 tiêu chí. Đây là lý do từng tiêu chí được chọn:

**1. Cú pháp & ngôn ngữ**
Ảnh hưởng trực tiếp đến tốc độ viết, khả năng đọc khi review.

**2. Khả năng tái sử dụng**
VKhi API có nhiều endpoints, việc định nghĩa cùng một error response hay pagination tốn nhiều công sức. Mỗi format giải quyết vấn đề này theo cách khác nhau.

**3. Tooling & ecosystem**
Spec chỉ có giá trị nếu có tool xung quanh nó.

**4. Code generation**
Khả năng sinh client SDK hoặc server stub từ spec.
---

