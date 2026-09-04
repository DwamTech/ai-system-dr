# research_extractor.py - استخراج أقسام البحث العلمي العربي
# =========================================================
# مكتبة ذكية لاستخراج أقسام الأبحاث العلمية باستخدام regex

import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ResearchSection:
    """قسم من أقسام البحث العلمي"""
    title: str
    content: str
    confidence: float  # 0.0 - 1.0

class ArabicResearchExtractor:
    """
    مستخرج أقسام البحث العلمي العربي
    يستخرج: الأهداف، الأسئلة، المشكلة، النتائج، التوصيات
    """
    
    # أنماط البحث لكل قسم
    PATTERNS = {
        "objectives": {
            "title": "🎯 أهداف الدراسة",
            "patterns": [
                r"(?:أهداف\s*(?:الدراسة|البحث|الرسالة))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:يهدف\s*(?:البحث|هذا البحث|الدراسة))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:الهدف\s*(?:الرئيسي|العام|من الدراسة))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:تهدف\s*(?:الدراسة|هذه الدراسة))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
            ]
        },
        "questions": {
            "title": "❓ أسئلة الدراسة",
            "patterns": [
                r"(?:أسئلة\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:تساؤلات\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:السؤال\s*(?:الرئيسي|الأول|الثاني))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
                r"(?:تسعى\s*الدراسة\s*للإجابة\s*(?:عن|على))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
            ]
        },
        "problem": {
            "title": "🔴 مشكلة الدراسة",
            "patterns": [
                r"(?:مشكلة\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:إشكالية\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:تتمثل\s*المشكلة\s*في)[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
                r"(?:تتلخص\s*مشكلة\s*البحث)[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
            ]
        },
        "results": {
            "title": "📋 نتائج الدراسة",
            "patterns": [
                r"(?:نتائج\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,8})",
                r"(?:توصلت\s*(?:الدراسة|الباحث|الباحثة))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:أهم\s*النتائج)[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,8})",
                r"(?:أسفرت\s*(?:الدراسة|النتائج)\s*(?:عن|إلى))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:كشفت\s*(?:الدراسة|النتائج)\s*(?:عن|أن))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
            ]
        },
        "recommendations": {
            "title": "💡 توصيات الدراسة",
            "patterns": [
                r"(?:توصيات\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,8})",
                r"(?:توصي\s*(?:الدراسة|الباحث|الباحثة))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:يوصي\s*(?:البحث|الباحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:في\s*ضوء\s*(?:النتائج|ما\s*سبق))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
                r"(?:المقترحات)[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,5})",
            ]
        },
        "methodology": {
            "title": "🔬 منهج الدراسة",
            "patterns": [
                r"(?:منهج\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
                r"(?:استخدم(?:ت)?\s*(?:الدراسة|الباحث|الباحثة)\s*المنهج)[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
                r"(?:المنهج\s*المستخدم)[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
            ]
        },
        "sample": {
            "title": "👥 عينة الدراسة",
            "patterns": [
                r"(?:عينة\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
                r"(?:مجتمع\s*(?:الدراسة|البحث))[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
                r"(?:تكون(?:ت)?\s*العينة\s*من)[:\s]*([^.؟!]+(?:[.؟!][^.؟!]+){0,3})",
            ]
        }
    }
    
    def __init__(self):
        # تجميع الأنماط مسبقاً لتحسين الأداء
        self._compiled_patterns = {}
        for section, data in self.PATTERNS.items():
            self._compiled_patterns[section] = {
                "title": data["title"],
                "patterns": [re.compile(p, re.UNICODE | re.MULTILINE | re.IGNORECASE) 
                            for p in data["patterns"]]
            }
    
    def extract_section(self, text: str, section_name: str) -> Optional[ResearchSection]:
        """استخراج قسم معين من النص"""
        if section_name not in self._compiled_patterns:
            return None
        
        section_data = self._compiled_patterns[section_name]
        best_match = None
        best_confidence = 0.0
        
        for i, pattern in enumerate(section_data["patterns"]):
            matches = pattern.findall(text)
            if matches:
                # الأنماط الأولى أكثر دقة
                confidence = 1.0 - (i * 0.1)
                content = max(matches, key=len)  # اختيار أطول تطابق
                
                if len(content) > 20 and confidence > best_confidence:
                    best_match = content.strip()
                    best_confidence = confidence
        
        if best_match:
            return ResearchSection(
                title=section_data["title"],
                content=best_match,
                confidence=best_confidence
            )
        return None
    
    def extract_all_sections(self, text: str) -> Dict[str, ResearchSection]:
        """استخراج جميع أقسام البحث من النص"""
        results = {}
        for section_name in self.PATTERNS.keys():
            section = self.extract_section(text, section_name)
            if section:
                results[section_name] = section
        return results
    
    def get_formatted_report(self, text: str) -> str:
        """إنشاء تقرير منسق بأقسام البحث"""
        sections = self.extract_all_sections(text)
        
        if not sections:
            return "⚠️ لم يتم العثور على أقسام بحثية واضحة في النص."
        
        report = "# 📑 تحليل أقسام البحث العلمي\n\n"
        report += f"**عدد الأقسام المستخرجة:** {len(sections)}\n\n"
        report += "---\n\n"
        
        for section_name, section in sections.items():
            confidence_bar = "🟢" if section.confidence >= 0.8 else "🟡" if section.confidence >= 0.5 else "🔴"
            report += f"## {section.title} {confidence_bar}\n\n"
            report += f"{section.content}\n\n"
            report += "---\n\n"
        
        return report


# مثيل عام للاستخدام السريع
_extractor = ArabicResearchExtractor()

def extract_research_sections(text: str) -> Dict[str, ResearchSection]:
    """دالة مختصرة لاستخراج أقسام البحث"""
    return _extractor.extract_all_sections(text)

def get_research_report(text: str) -> str:
    """دالة مختصرة للحصول على تقرير أقسام البحث"""
    return _extractor.get_formatted_report(text)
