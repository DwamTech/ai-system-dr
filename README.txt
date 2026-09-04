╔════════════════════════════════════════════════════════════╗
║              معلومات بيانات Docker المحفوظة              ║
╚════════════════════════════════════════════════════════════╝

📅 تاريخ الحفظ: 2026-02-12
💻 المشروع: MySearchEngine
📁 الموقع: .\دوكر البيانات

📦 الملفات المحفوظة:
  ✓ opensearch_data.tar.gz - جميع المستندات المفهرسة
  ✓ ollama_data.tar.gz - النماذج اللغوية المحملة

🎯 الغرض:
  هذا المجلد يحتوي على جميع بيانات Docker Volumes للمشروع.
  يمكن نقله بسهولة إلى جهاز آخر أو رفعه على Google Drive.

📝 كيفية الاستعادة على جهاز آخر:
  1. انسخ مجلد "دوكر البيانات" بالكامل للجهاز الجديد
  2. ضعه في مجلد المشروع
  3. افتح PowerShell في مجلد المشروع
  4. شغّل الأمر التالي:
     
     PowerShell -ExecutionPolicy Bypass -File .\restore_docker_data.ps1

🚀 طرق النقل:

  1️⃣ Google Drive:
     - ارفع مجلد "دوكر البيانات" على Google Drive
     - على الجهاز الجديد، حمّله من Drive
     
  2️⃣ فلاشة USB:
     - انسخ المجلد على الفلاشة
     - على الجهاز الجديد، انسخه من الفلاشة
     
  3️⃣ Network Share:
     - شارك المجلد على الشبكة
     - على الجهاز الجديد، انسخه من الشبكة

⚠️  ملاحظات مهمة:
  - لا تحذف هذا المجلد حتى تتأكد من نجاح النقل
  - تأكد من وجود Docker Desktop على الجهاز الجديد
  - الملفات مضغوطة لتوفير المساحة
  - يمكن استعادة البيانات في أي وقت

🔧 أوامر مفيدة:

  • حفظ البيانات مرة أخرى:
    PowerShell -ExecutionPolicy Bypass -File .\save_docker_data.ps1

  • استعادة البيانات:
    PowerShell -ExecutionPolicy Bypass -File .\restore_docker_data.ps1

  • فحص حالة Docker:
    PowerShell -ExecutionPolicy Bypass -File .\check_docker_status.ps1

📚 للمزيد من المعلومات:
  راجع الأدلة التالية في مجلد brain:
  - docker_migration_guide.md
  - usb_migration_guide.md
  - migration_action_plan.md

✨ تم إنشاء هذا الملف تلقائياً بواسطة save_docker_data.ps1
