# web_search.py
# ============================================
# SearXNG Integration for Web & Academic Search
# ============================================

import os
import threading
import time
import requests
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


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
    _circuit_lock = threading.Lock()
    _circuit_open_until = 0.0
    _capabilities = None
    _capabilities_checked_at = 0.0
    
    def __init__(self, searxng_url=None):
        """
        Args:
            searxng_url: رابط SearXNG (مثل http://localhost:8080)
        """
        self.base_url = searxng_url or os.getenv("SEARXNG_URL", "http://localhost:8888")
        self._available = None
        self._available_checked_at = 0.0
        self._health_ttl_seconds = float(os.getenv("SEARXNG_HEALTH_TTL_SECONDS", "15"))
        retry = Retry(total=2, connect=2, read=1, backoff_factor=0.25, status_forcelist=(502, 503, 504), allowed_methods=("GET",))
        self.session = requests.Session()
        self.session.mount("http://", HTTPAdapter(max_retries=retry))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def _open_circuit(self) -> None:
        with self._circuit_lock:
            type(self)._circuit_open_until = time.monotonic() + self._health_ttl_seconds

    def available_engines(self) -> set[str]:
        current = time.monotonic()
        cls = type(self)
        if cls._capabilities is not None and current - cls._capabilities_checked_at < self._health_ttl_seconds:
            return set(cls._capabilities)
        try:
            response = self.session.get(f"{self.base_url}/config", timeout=(3, 5))
            response.raise_for_status()
            engines = {
                str(item.get("name", "")).strip().casefold()
                for item in response.json().get("engines", [])
                if not item.get("disabled") and item.get("name")
            }
        except Exception:
            engines = set()
        cls._capabilities, cls._capabilities_checked_at = engines, current
        return engines
    
    @property
    def is_available(self) -> bool:
        """تحقق من توفر SearXNG"""
        if time.monotonic() < type(self)._circuit_open_until:
            return False
        if self._available is not None and (time.monotonic() - self._available_checked_at) < self._health_ttl_seconds:
            return self._available
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=(2, 3))
            self._available = response.status_code == 200
        except Exception:
            self._available = False
        if not self._available:
            self._open_circuit()
        self._available_checked_at = time.monotonic()
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
        query = query.strip()
        if not query:
            return {"success": False, "results": [], "query": query, "total": 0, "error": "اكتب نص البحث أولاً."}
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
            
            available = self.available_engines()
            # لا نرسل محركًا غير متاح، ولا نسقط بصمت إلى تصنيف مختلف.
            if eng_category == "science":
                academic = [name for name in ("google scholar", "arxiv", "semantic scholar", "pubmed", "openairepublications") if name in available]
                if not academic:
                    return {"success": False, "results": [], "query": query, "total": 0, "error": "لا يوجد محرك أكاديمي متاح حاليًا."}
                params["engines"] = ",".join(academic)
            elif category == "ويكيبيديا":
                if "wikipedia" not in available:
                    return {"success": False, "results": [], "query": query, "total": 0, "error": "محرك ويكيبيديا غير متاح حاليًا."}
                params["engines"] = "wikipedia"
            
            response = self.session.get(
                f"{self.base_url}/search",
                params=params,
                timeout=(3, 15)
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "results": [],
                    "query": query,
                    "total": 0,
                    "error": "البحث الأكاديمي غير متاح مؤقتاً. حاول مرة أخرى لاحقاً."
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
                "success": bool(results),
                "results": results,
                "query": query,
                "total": len(results),
                "suggestions": data.get("suggestions", []),
                "error": None if results else "لم يتم العثور على نتائج."
            }
            
        except requests.Timeout:
            self._available = None
            self._open_circuit()
            return {
                "success": False,
                "results": [],
                "query": query,
                "total": 0,
                "error": "انتهت مهلة البحث. حاول مرة أخرى."
            }
        except Exception:
            self._available = None
            self._open_circuit()
            return {
                "success": False,
                "results": [],
                "query": query,
                "total": 0,
                "error": "البحث الأكاديمي غير متاح مؤقتاً. حاول مرة أخرى لاحقاً."
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
