# utils.py - الأدوات المساعدة المحسنة للنظام
# ==========================================
# ملف الأدوات المساعدة لمحرك البحث الأكاديمي
# ==========================================

import streamlit as st
from functools import lru_cache
from datetime import datetime
import os
import json
import hashlib
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
import urllib.parse

# ==========================================
# 1. إعدادات النظام
# ==========================================

# مسار حفظ البيانات
DATA_DIR = Path("data")
TICKETS_DIR = DATA_DIR / "support_tickets"
DOWNLOADS_DIR = DATA_DIR / "downloads"
CACHE_DIR = DATA_DIR / "cache"

# إنشاء المجلدات إذا لم تكن موجودة
for directory in [DATA_DIR, TICKETS_DIR, DOWNLOADS_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2. دوال البحث الأكاديمي
# ==========================================

@lru_cache(maxsize=2000)
def get_scholar_link_cached(filename: str) -> str:
    """
    إنشاء رابط Google Scholar للبحث عن ملف معين
    
    Args:
        filename: اسم الملف للبحث عنه
        
    Returns:
        رابط Google Scholar للبحث
    """
    # تنظيف اسم الملف
    clean_name = filename
    
    # إزالة الامتدادات الشائعة
    extensions_to_remove = ['.pdf', '.docx', '.doc', '.txt', '.epub']
    for ext in extensions_to_remove:
        clean_name = clean_name.replace(ext, '')
    
    # تنظيف الرموز والأرقام الزائدة
    replacements = {
        '_': ' ',
        '-': ' ',
        '(': '',
        ')': '',
        '[': '',
        ']': '',
        '{': '',
        '}': '',
    }
    
    for old, new in replacements.items():
        clean_name = clean_name.replace(old, new)
    
    # إزالة المسافات المتعددة
    while '  ' in clean_name:
        clean_name = clean_name.replace('  ', ' ')
    
    clean_name = clean_name.strip()
    
    # ترميز النص للـ URL
    encoded_query = urllib.parse.quote(clean_name)
    
    # إنشاء الرابط
    base_url = "https://scholar.google.com/scholar"
    return f"{base_url}?q={encoded_query}"


def get_research_gate_link(filename: str) -> str:
    """إنشاء رابط ResearchGate للبحث"""
    clean_name = filename.replace('.pdf', '').replace('_', ' ').strip()
    encoded_query = urllib.parse.quote(clean_name)
    return f"https://www.researchgate.net/search?q={encoded_query}"


def get_semantic_scholar_link(filename: str) -> str:
    """إنشاء رابط Semantic Scholar للبحث"""
    clean_name = filename.replace('.pdf', '').replace('_', ' ').strip()
    encoded_query = urllib.parse.quote(clean_name)
    return f"https://www.semanticscholar.org/search?q={encoded_query}"


# ==========================================
# 3. نظام تذاكر الدعم المحسن
# ==========================================

def save_support_ticket_optimized(
    name: str,
    email: str,
    query_type: str,
    message: str,
    rating: int
) -> Dict[str, Any]:
    """
    حفظ تذكرة دعم جديدة مع معلومات شاملة
    
    Args:
        name: اسم المستخدم
        email: البريد الإلكتروني
        query_type: نوع الاستفسار
        message: الرسالة
        rating: التقييم (1-5)
        
    Returns:
        بيانات التذكرة المحفوظة
    """
    # إنشاء معرف فريد للتذكرة
    ticket_id = hashlib.md5(
        f"{datetime.now().isoformat()}{email}{message}".encode()
    ).hexdigest()[:12].upper()
    
    # بيانات التذكرة
    ticket_data = {
        "ticket_id": f"TKT-{ticket_id}",
        "created_at": datetime.now().isoformat(),
        "status": "new",
        "priority": _calculate_priority(rating, query_type),
        "user_info": {
            "name": name if name else "مجهول",
            "email": email if email else "غير محدد"
        },
        "ticket_details": {
            "type": query_type,
            "message": message,
            "rating": rating,
            "rating_stars": "⭐" * rating
        },
        "system_info": {
            "session_id": st.session_state.get('session_id', 'unknown'),
            "timestamp_unix": datetime.now().timestamp()
        }
    }
    
    # حفظ التذكرة في ملف JSON
    ticket_file = TICKETS_DIR / f"ticket_{ticket_id}.json"
    try:
        with open(ticket_file, 'w', encoding='utf-8') as f:
            json.dump(ticket_data, f, ensure_ascii=False, indent=2)
        
        # تحديث ملف الفهرس
        _update_tickets_index(ticket_data)
        
        return ticket_data
        
    except Exception as e:
        st.error(f"خطأ في حفظ التذكرة: {e}")
        return {"error": str(e)}


def _calculate_priority(rating: int, query_type: str) -> str:
    """حساب أولوية التذكرة"""
    if query_type == "مشكلة تقنية":
        return "عالية" if rating <= 2 else "متوسطة"
    elif rating <= 2:
        return "متوسطة"
    return "عادية"


def _update_tickets_index(ticket_data: Dict) -> None:
    """تحديث فهرس التذاكر"""
    index_file = TICKETS_DIR / "index.json"
    
    try:
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {"total_tickets": 0, "tickets": []}
        
        index["total_tickets"] += 1
        index["tickets"].append({
            "id": ticket_data["ticket_id"],
            "date": ticket_data["created_at"],
            "type": ticket_data["ticket_details"]["type"],
            "status": ticket_data["status"]
        })
        
        # الاحتفاظ بآخر 1000 تذكرة فقط
        index["tickets"] = index["tickets"][-1000:]
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
            
    except Exception:
        pass  # تجاهل أخطاء الفهرس


# ==========================================
# 4. أزرار التحميل المحسنة
# ==========================================

def create_fancy_download_button_optimized(
    content: str,
    prefix: str,
    label: str,
    file_type: str = "txt",
    icon: str = "📥"
) -> str:
    """
    إنشاء زر تحميل محسن وأنيق
    
    Args:
        content: المحتوى للتحميل
        prefix: بادئة اسم الملف
        label: نص الزر
        file_type: نوع الملف (txt, md, json)
        icon: أيقونة الزر
        
    Returns:
        اسم الملف المنشأ
    """
    # تحديد نوع MIME
    mime_types = {
        "txt": "text/plain",
        "md": "text/markdown",
        "json": "application/json",
        "html": "text/html"
    }
    mime_type = mime_types.get(file_type, "text/plain")
    
    # إنشاء اسم ملف فريد
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{file_type}"
    
    # إضافة معلومات الهيدر للملف
    header = f"""# ═══════════════════════════════════════════════════════════
# 📄 {filename}
# 📅 التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# 🔧 تم إنشاؤه بواسطة: محرك البحث الأكاديمي المحسن
# ═══════════════════════════════════════════════════════════

"""
    
    full_content = header + content
    
    # إنشاء الزر
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.download_button(
            label=f"{icon} {label}",
            data=full_content.encode('utf-8'),
            file_name=filename,
            mime=mime_type,
            use_container_width=True,
            key=f"download_{filename}"
        )
    
    with col2:
        # عرض حجم الملف
        file_size = len(full_content.encode('utf-8'))
        st.caption(f"📊 {format_file_size(file_size)}")
    
    return filename


def create_multi_format_download(
    content: str,
    prefix: str,
    title: str = "خيارات التحميل"
) -> None:
    """
    إنشاء خيارات تحميل متعددة الصيغ
    """
    with st.expander(f"📦 {title}", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            create_fancy_download_button_optimized(
                content, prefix, "نص عادي", "txt", "📄"
            )
        
        with col2:
            # تحويل إلى Markdown
            md_content = f"# {prefix}\n\n{content}"
            create_fancy_download_button_optimized(
                md_content, prefix, "Markdown", "md", "📝"
            )
        
        with col3:
            # تحويل إلى HTML
            html_content = f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>{prefix}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; line-height: 1.8; }}
        .content {{ max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
    <div class="content">
        <h1>{prefix}</h1>
        <p>{content.replace(chr(10), '<br>')}</p>
    </div>
</body>
</html>"""
            create_fancy_download_button_optimized(
                html_content, prefix, "HTML", "html", "🌐"
            )


# ==========================================
# 5. تنسيق الأحجام والأرقام
# ==========================================

def format_file_size(size_bytes: int) -> str:
    """
    تنسيق حجم الملف بشكل قابل للقراءة
    
    Args:
        size_bytes: الحجم بالبايت
        
    Returns:
        نص منسق للحجم
    """
    if size_bytes < 0:
        return "غير صالح"
    
    # وحدات القياس
    units = [
        ("B", 1),
        ("KB", 1024),
        ("MB", 1024 ** 2),
        ("GB", 1024 ** 3),
        ("TB", 1024 ** 4)
    ]
    
    for unit_name, unit_size in reversed(units):
        if size_bytes >= unit_size:
            value = size_bytes / unit_size
            # تنسيق الأرقام العربية
            if value < 10:
                return f"{value:.2f} {unit_name}"
            elif value < 100:
                return f"{value:.1f} {unit_name}"
            else:
                return f"{value:.0f} {unit_name}"
    
    return f"{size_bytes} B"


def format_number_arabic(number: int) -> str:
    """تنسيق الأرقام بالصيغة العربية"""
    arabic_numerals = {
        '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
        '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
    }
    formatted = f"{number:,}"
    return ''.join(arabic_numerals.get(c, c) for c in formatted)


def format_duration(seconds: float) -> str:
    """تنسيق المدة الزمنية"""
    if seconds < 1:
        return f"{seconds * 1000:.0f} مللي ثانية"
    elif seconds < 60:
        return f"{seconds:.1f} ثانية"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} دقيقة"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} ساعة"


# ==========================================
# 6. أدوات التخزين المؤقت
# ==========================================

class SmartCache:
    """نظام تخزين مؤقت ذكي"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """الحصول على قيمة من الذاكرة المؤقتة"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now().timestamp() - entry['timestamp'] < self.ttl_seconds:
                entry['hits'] += 1
                return entry['value']
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """تخزين قيمة في الذاكرة المؤقتة"""
        if len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        self._cache[key] = {
            'value': value,
            'timestamp': datetime.now().timestamp(),
            'hits': 0
        }
    
    def _evict_oldest(self) -> None:
        """حذف أقدم العناصر"""
        if self._cache:
            oldest_key = min(self._cache, key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]
    
    def clear(self) -> None:
        """مسح الذاكرة المؤقتة"""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """إحصائيات الذاكرة المؤقتة"""
        total_hits = sum(entry['hits'] for entry in self._cache.values())
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'total_hits': total_hits,
            'usage_percent': (len(self._cache) / self.max_size) * 100
        }


# ==========================================
# 7. أدوات التحقق والتنظيف
# ==========================================

def sanitize_filename(filename: str) -> str:
    """تنظيف اسم الملف من الأحرف غير المسموحة"""
    # الأحرف غير المسموحة في أسماء الملفات
    invalid_chars = '<>:"/\\|?*'
    
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # إزالة النقاط من البداية والنهاية
    filename = filename.strip('. ')
    
    # تحديد الطول الأقصى
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    
    return filename


def validate_pdf_file(file) -> tuple[bool, str]:
    """التحقق من صلاحية ملف PDF"""
    if file is None:
        return False, "لم يتم اختيار ملف"
    
    # التحقق من الامتداد
    if not file.name.lower().endswith('.pdf'):
        return False, "الملف ليس بصيغة PDF"
    
    # التحقق من الحجم (الحد الأقصى 100MB)
    max_size = 100 * 1024 * 1024
    if file.size > max_size:
        return False, f"حجم الملف يتجاوز الحد الأقصى ({format_file_size(max_size)})"
    
    # التحقق من التوقيع السحري لـ PDF
    file.seek(0)
    header = file.read(5)
    file.seek(0)
    
    if header != b'%PDF-':
        return False, "الملف ليس ملف PDF صالح"
    
    return True, "ملف صالح"


# ==========================================
# 8. أدوات العرض والتنسيق
# ==========================================

def display_metric_card(
    title: str,
    value: Any,
    delta: Optional[str] = None,
    icon: str = "📊",
    color: str = "#4CAF50"
) -> None:
    """عرض بطاقة مقياس أنيقة"""
    delta_html = f"<small style='color: {'green' if delta and delta.startswith('+') else 'red'}'>{delta}</small>" if delta else ""
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}22 0%, {color}11 100%);
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 15px;
        margin: 5px 0;
    ">
        <div style="font-size: 14px; color: #666;">{icon} {title}</div>
        <div style="font-size: 24px; font-weight: bold; color: #333;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def display_progress_with_status(
    current: int,
    total: int,
    status: str,
    show_percentage: bool = True
) -> None:
    """عرض شريط تقدم مع حالة"""
    progress = current / total if total > 0 else 0
    percentage = f" ({progress * 100:.1f}%)" if show_percentage else ""
    
    st.progress(progress, text=f"{status}{percentage}")


# ==========================================
# 9. تصدير الدوال العامة
# ==========================================

__all__ = [
    # دوال البحث
    'get_scholar_link_cached',
    'get_research_gate_link',
    'get_semantic_scholar_link',
    
    # نظام الدعم
    'save_support_ticket_optimized',
    
    # أزرار التحميل
    'create_fancy_download_button_optimized',
    'create_multi_format_download',
    
    # تنسيق الأرقام
    'format_file_size',
    'format_number_arabic',
    'format_duration',
    
    # أدوات التخزين
    'SmartCache',
    
    # أدوات التحقق
    'sanitize_filename',
    'validate_pdf_file',
    
    # أدوات العرض
    'display_metric_card',
    'display_progress_with_status',
]
