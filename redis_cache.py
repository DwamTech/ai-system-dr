# redis_cache.py
# ============================================
# Redis-based caching with fallback to in-memory dict
# ============================================

import json
import hashlib
import time
import os


class SmartCache:
    """
    Cache ذكي يستخدم Redis كأساس مع fallback لـ dict عادي.
    - يدعم TTL (انتهاء صلاحية تلقائي)
    - يخزن أي نوع بيانات عبر JSON serialization
    - يحسب cache hit rate
    """
    
    def __init__(self, redis_url=None, default_ttl=1800):
        """
        Args:
            redis_url: رابط Redis (مثل redis://localhost:6379/0)
            default_ttl: مدة صلاحية الـ cache بالثواني (افتراضي 30 دقيقة)
        """
        self.default_ttl = default_ttl
        self._redis = None
        self._fallback_cache = {}  # dict عادي كـ fallback
        self._fallback_timestamps = {}  # لتتبع TTL في الـ fallback
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
        
        # محاولة الاتصال بـ Redis
        redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6380/0")
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True, socket_timeout=3)
            self._redis.ping()
        except Exception:
            self._redis = None
    
    @property
    def is_redis_available(self):
        """هل Redis متاح؟"""
        if self._redis is None:
            return False
        try:
            self._redis.ping()
            return True
        except Exception:
            return False
    
    def _make_key(self, query: str) -> str:
        """إنشاء مفتاح فريد من الاستعلام"""
        return f"nlp_cache:{hashlib.md5(query.encode('utf-8')).hexdigest()}"
    
    def get(self, query: str):
        """
        جلب نتيجة من الـ cache.
        Returns: القيمة المخزنة أو None
        """
        key = self._make_key(query)
        
        # المحاولة من Redis أولاً
        if self.is_redis_available:
            try:
                value = self._redis.get(key)
                if value is not None:
                    self._stats["hits"] += 1
                    return json.loads(value)
                self._stats["misses"] += 1
                return None
            except Exception:
                self._stats["errors"] += 1
        
        # Fallback إلى dict
        if key in self._fallback_cache:
            # تحقق من TTL
            timestamp = self._fallback_timestamps.get(key, 0)
            if time.time() - timestamp < self.default_ttl:
                self._stats["hits"] += 1
                return self._fallback_cache[key]
            else:
                # انتهت الصلاحية
                del self._fallback_cache[key]
                del self._fallback_timestamps[key]
        
        self._stats["misses"] += 1
        return None
    
    def set(self, query: str, value, ttl=None):
        """
        تخزين نتيجة في الـ cache.
        Args:
            query: الاستعلام
            value: القيمة (يجب أن تكون JSON serializable)
            ttl: مدة الصلاحية بالثواني (None = استخدم الافتراضي)
        """
        key = self._make_key(query)
        ttl = ttl or self.default_ttl
        
        # تخزين في Redis
        if self.is_redis_available:
            try:
                self._redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
                return True
            except Exception:
                self._stats["errors"] += 1
        
        # Fallback: تخزين في dict
        self._fallback_cache[key] = value
        self._fallback_timestamps[key] = time.time()
        
        # حماية الذاكرة: مسح أقدم 20% لو الحجم كبير
        if len(self._fallback_cache) > 1000:
            sorted_keys = sorted(self._fallback_timestamps, key=self._fallback_timestamps.get)
            for old_key in sorted_keys[:200]:
                self._fallback_cache.pop(old_key, None)
                self._fallback_timestamps.pop(old_key, None)
        
        return True
    
    def clear(self):
        """مسح كل الـ cache"""
        if self.is_redis_available:
            try:
                # مسح المفاتيح المتعلقة بالتطبيق فقط
                keys = self._redis.keys("nlp_cache:*")
                if keys:
                    self._redis.delete(*keys)
            except Exception:
                pass
        
        self._fallback_cache.clear()
        self._fallback_timestamps.clear()
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
    
    def get_stats(self) -> dict:
        """إحصائيات الأداء"""
        total = self._stats["hits"] + self._stats["misses"]
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "hit_rate": (self._stats["hits"] / total * 100) if total > 0 else 0,
            "backend": "Redis" if self.is_redis_available else "In-Memory",
            "size": self._get_cache_size()
        }
    
    def _get_cache_size(self) -> int:
        """عدد العناصر في الـ cache"""
        if self.is_redis_available:
            try:
                keys = self._redis.keys("nlp_cache:*")
                return len(keys)
            except Exception:
                pass
        return len(self._fallback_cache)
