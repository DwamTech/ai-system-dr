# web_search.py
# ============================================
# SearXNG Integration for Web & Academic Search
# ============================================

import os
import requests
from typing import Optional


class WebSearchEngine:
    """
    محرك بحث على الإنترنت باستخدام SearXNG.
    يدعم البحث العام والأكاديمي (arXiv, Google Scholar, PubMed, إلخ).
    """
    
    CATEGORIES = {
        "عام": "general",
        "أكاديمي": "science",
        "صور": "images",
        "أخبار": "news",
        "ويكيبيديا": "general",
    }
    
    def __init__(self, searxng_url=None):
        """
        Args:
            searxng_url: رابط SearXNG (مثل http://localhost:8080)
        """
        self.base_url = searxng_url or os.getenv("SEARXNG_URL", "http://localhost:8888")
        self._available = None
    
    @property
    def is_available(self) -> bool:
        """تحقق من توفر SearXNG"""
        if self._available is not None:
            return self._available
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=3)
            self._available = response.status_code == 200
        except Exception:
            self._available = False
        return self._available
    
    def search(self, query: str, category: str = "عام", language: str = "ar",
               max_results: int = 10) -> dict:
        """
        البحث في الإنترنت عبر SearXNG.
        
        Args:
            query: نص البحث
            category: التصنيف (عام، أكاديمي، صور، أخبار، ويكيبيديا)
            language: لغة البحث (ar, en)
            max_results: عدد النتائج القصوى
        
        Returns:
            dict مع المفاتيح: success, results, query, total, error
        """
        if not self.is_available:
            return {
                "success": False,
                "results": [],
                "query": query,
                "total": 0,
                "error": "SearXNG غير متاح. تأكد من تشغيل حاوية SearXNG."
            }
        
        try:
            # تحويل التصنيف العربي للإنجليزي
            eng_category = self.CATEGORIES.get(category, "general")
            
            # بناء الطلب
            params = {
                "q": query,
                "format": "json",
                "categories": eng_category,
                "language": language,
                "pageno": 1,
            }
            
            # إضافة محركات أكاديمية للبحث الأكاديمي
            if eng_category == "science":
                params["engines"] = "google scholar,arxiv,semantic scholar,pubmed"
            
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=15
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "results": [],
                    "query": query,
                    "total": 0,
                    "error": f"خطأ في SearXNG: HTTP {response.status_code}"
                }
            
            data = response.json()
            results = []
            
            for item in data.get("results", [])[:max_results]:
                result = {
                    "title": item.get("title", "بدون عنوان"),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "engine": item.get("engine", "غير محدد"),
                    "score": item.get("score", 0),
                    "publishedDate": item.get("publishedDate", ""),
                    "category": category,
                }
                
                # إضافة معلومات أكاديمية إن وجدت
                if "doi" in item:
                    result["doi"] = item["doi"]
                if "authors" in item:
                    result["authors"] = item["authors"]
                if "journal" in item:
                    result["journal"] = item["journal"]
                
                results.append(result)
            
            return {
                "success": True,
                "results": results,
                "query": query,
                "total": len(results),
                "suggestions": data.get("suggestions", []),
                "error": None
            }
            
        except requests.Timeout:
            return {
                "success": False,
                "results": [],
                "query": query,
                "total": 0,
                "error": "انتهت مهلة البحث. حاول مرة أخرى."
            }
        except Exception as e:
            return {
                "success": False,
                "results": [],
                "query": query,
                "total": 0,
                "error": f"خطأ في البحث: {str(e)}"
            }
    
    def search_academic(self, query: str, max_results: int = 10) -> dict:
        """بحث أكاديمي مباشر (arXiv, Google Scholar, PubMed)"""
        return self.search(query, category="أكاديمي", max_results=max_results)
    
    def search_general(self, query: str, max_results: int = 10) -> dict:
        """بحث عام (Google, Bing, DuckDuckGo)"""
        return self.search(query, category="عام", max_results=max_results)
    
    def format_results_markdown(self, search_result: dict) -> str:
        """تحويل النتائج إلى Markdown للعرض"""
        if not search_result["success"]:
            return f"❌ {search_result['error']}"
        
        if not search_result["results"]:
            return "لم يتم العثور على نتائج."
        
        output = f"### 🔍 نتائج البحث: \"{search_result['query']}\"\n\n"
        output += f"📊 تم العثور على **{search_result['total']}** نتيجة\n\n---\n\n"
        
        for i, result in enumerate(search_result["results"], 1):
            output += f"#### {i}. {result['title']}\n"
            
            if result.get("content"):
                output += f"> {result['content'][:300]}...\n\n" if len(result.get("content", "")) > 300 else f"> {result['content']}\n\n"
            
            output += f"🔗 [{result['url']}]({result['url']})\n"
            output += f"🔧 المحرك: `{result['engine']}`"
            
            if result.get("publishedDate"):
                output += f" | 📅 {result['publishedDate']}"
            if result.get("authors"):
                output += f"\n👥 المؤلفون: {', '.join(result['authors'][:3])}"
            if result.get("doi"):
                output += f"\n📄 DOI: `{result['doi']}`"
            
            output += "\n\n---\n\n"
        
        # اقتراحات
        if search_result.get("suggestions"):
            output += "💡 **اقتراحات بحث:**\n"
            for s in search_result["suggestions"][:5]:
                output += f"- {s}\n"
        
        return output
