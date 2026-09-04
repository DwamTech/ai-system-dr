# arabic_text_processor.py
"""
معالج النصوص العربية المحسّن
يدعم إعادة تشكيل النص و RTL و التطبيع
"""

import re
from typing import Optional

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False
    print("⚠️ arabic-reshaper & python-bidi not installed. Arabic text may not display correctly.")


class ArabicTextProcessor:
    """معالج شامل للنصوص العربية"""
    
    def __init__(self):
        self.support_available = ARABIC_SUPPORT
    
    def reshape_for_display(self, text: str) -> str:
        """
        إعادة تشكيل النص العربي للعرض الصحيح
        
        Args:
            text: النص العربي
        
        Returns:
            النص المعاد تشكيله للعرض
        """
        if not self.support_available or not text:
            return text
        
        try:
            # إعادة تشكيل الأحرف العربية
            reshaped_text = arabic_reshaper.reshape(text)
            # تطبيق خوارزمية BiDi للعرض الصحيح
            display_text = get_display(reshaped_text)
            return display_text
        except Exception as e:
            print(f"Error reshaping Arabic text: {e}")
            return text
    
    def normalize_arabic(self, text: str) -> str:
        """
        تطبيع النص العربي (توحيد الأحرف المتشابهة)
        
        Args:
            text: النص العربي
        
        Returns:
            النص المطبّع
        """
        if not text:
            return text
        
        # إزالة التش كيل
        text = self.remove_diacritics(text)
        
        # توحيد الهمزات
        text = re.sub(r'[إأآٱ]', 'ا', text)
        text = re.sub(r'[ىئ]', 'ي', text)
        text = re.sub(r'ؤ', 'و', text)
        text = re.sub(r'ة', 'ه', text)
        
        # توحيد المسافات
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def remove_diacritics(self, text: str) -> str:
        """
        إزالة التشكيل من النص العربي
        
        Args:
            text: النص العربي
        
        Returns:
            النص بدون تشكيل
        """
        if not text:
            return text
        
        # نطاق Unicode للتشكيل العربي
        diacritics = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
        return diacritics.sub('', text)
    
    def clean_arabic_text(self, text: str, keep_english: bool = True) -> str:
        """
        تنظيف النص العربي من الأحرف غير المرغوبة
        
        Args:
            text: النص
            keep_english: الاحتفاظ بالأحرف الإنجليزية
        
        Returns:
            النص المنظف
        """
        if not text:
            return text
        
        if keep_english:
            # احتفظ بالعربي والإنجليزي والأرقام والعلامات الأساسية
            text = re.sub(r'[^\u0600-\u06FF\u0750-\u077Fa-zA-Z0-9\s\.\,\;\:\-\(\)\[\]\{\}\"\'\!\?]', ' ', text)
        else:
            # احتفظ بالعربي والأرقام والعلامات فقط
            text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F0-9\s\.\,\;\:\-\(\)\[\]\{\}\"\'\!\?]', ' ', text)
        
        # إزالة المسافات المتعددة
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def extract_arabic_sentences(self, text: str) -> list[str]:
        """
        استخراج الجمل العربية من النص
        
        Args:
            text: النص
        
        Returns:
            قائمة الجمل
        """
        if not text:
            return []
        
        # تقسيم بناءً على علامات الترقيم العربية والإنجليزية
        sentences = re.split(r'[\.؟\!\.\?]', text)
        
        # تنظيف الجمل
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def is_arabic(self, text: str, threshold: float = 0.3) -> bool:
        """
        فحص ما إذا كان النص عربياً
        
        Args:
            text: النص للفحص
            threshold: الحد الأدنى لنسبة الأحرف العربية
        
        Returns:
            True إذا كان النص عربياً
        """
        if not text:
            return False
        
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        total_chars = sum(1 for c in text if c.isalpha())
        
        if total_chars == 0:
            return False
        
        return (arabic_chars / total_chars) >= threshold
    
    def split_mixed_text(self, text: str) -> dict[str, list[str]]:
        """
        تقسيم النص المختلط (عربي + إنجليزي) إلى أجزاء
        
        Args:
            text: النص المختلط
        
        Returns:
            قاموس مع 'arabic' و 'english' و 'mixed'
        """
        result = {
            'arabic': [],
            'english': [],
            'mixed': [],
            'numbers': []
        }
        
        # تقسيم بناءً على المسافات والفقرات
        parts = re.split(r'(\s+)', text)
        
        for part in parts:
            if not part.strip():
                continue
            
            if self.is_arabic(part, threshold=0.8):
                result['arabic'].append(part)
            elif re.match(r'^[a-zA-Z]+$', part):
                result['english'].append(part)
            elif re.match(r'^[0-9]+$', part):
                result['numbers'].append(part)
            else:
                result['mixed'].append(part)
        
        return result
    
    def format_for_html(self, text: str, add_direction: bool = True) -> str:
        """
        تنسيق النص العربي لعرض HTML
        
        Args:
            text: النص العربي
            add_direction: إضافة خاصية dir="rtl"
        
        Returns:
            HTML منسق
        """
        if not text:
            return ""
        
        # إعادة التشكيل إذا كان متاحاً
        if self.support_available:
            text = self.reshape_for_display(text)
        
        # إضافة direction RTL
        if add_direction:
            return f'<div dir="rtl" style="text-align: right;">{text}</div>'
        else:
            return text
    
    def wrap_arabic_words(self, text: str, max_width: int = 50) -> str:
        """
        تقسيم النص العربي إلى أسطر حسب العرض
        
        Args:
            text: النص
            max_width: العرض الأقصى للسطر (بالأحرف)
        
        Returns:
            النص مقسم إلى أسطر
        """
        if not text:
            return text
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            
            if current_length + word_length + 1 <= max_width:
                current_line.append(word)
                current_length += word_length + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def highlight_keywords(
        self,
        text: str,
        keywords: list[str],
        highlight_color: str = "#FFEB3B"
    ) -> str:
        """
        تمييز الكلمات المفتاحية في النص
        
        Args:
            text: النص
            keywords: قائمة الكلمات المفتاحية
            highlight_color: لون التمييز
        
        Returns:
            نص HTML مع الكلمات المميزة
        """
        if not text or not keywords:
            return text
        
        highlighted_text = text
        
        for keyword in keywords:
            # استخدام regex للبحث عن الكلمة كاملة
            pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
            highlighted_text = pattern.sub(
                f'<mark style="background-color: {highlight_color}; padding: 2px 4px; border-radius: 3px;">{keyword}</mark>',
                highlighted_text
            )
        
        return highlighted_text


# Instance عام للاستخدام
arabic_processor = ArabicTextProcessor()


# ═══════════════════════════════════════════════════════════════
# Utility Functions (للاستخدام السريع)
# ═══════════════════════════════════════════════════════════════

def reshape_arabic(text: str) -> str:
    """دالة سريعة لإعادة تشكيل النص العربي"""
    return arabic_processor.reshape_for_display(text)


def normalize_arabic(text: str) -> str:
    """دالة سريعة لتطبيع النص العربي"""
    return arabic_processor.normalize_arabic(text)


def clean_arabic(text: str, keep_english: bool = True) -> str:
    """دالة سريعة لتنظيف النص العربي"""
    return arabic_processor.clean_arabic_text(text, keep_english)


def is_arabic_text(text: str) -> bool:
    """دالة سريعة للتحقق من النص العربي"""
    return arabic_processor.is_arabic(text)


# ═══════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════

__all__ = [
    'ArabicTextProcessor',
    'arabic_processor',
    'reshape_arabic',
    'normalize_arabic',
    'clean_arabic',
    'is_arabic_text',
    'ARABIC_SUPPORT'
]
