# test_project.py - ملف اختبار المشروع
# ==========================================
# اختبار شامل للتحقق من صحة الكود بدون الحاجة لـ Docker أو Ollama
# ==========================================

import sys
import os

# إضافة المسار للمشروع
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("🧪 بدء اختبار المشروع")
print("=" * 60)

# ==========================================
# 1. اختبار Syntax للملفات
# ==========================================
def test_syntax():
    """اختبار صحة Syntax لجميع ملفات Python"""
    print("\n📋 [1/5] اختبار Syntax...")
    
    files = [
        "app_optimized.py",
        "engine_optimized.py", 
        "processor_optimized.py",
        "utils.py"
    ]
    
    errors = []
    
    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, file, 'exec')
            print(f"   ✅ {file}")
        except SyntaxError as e:
            print(f"   ❌ {file}: {e}")
            errors.append((file, str(e)))
        except FileNotFoundError:
            print(f"   ⚠️ {file}: الملف غير موجود")
            errors.append((file, "الملف غير موجود"))
    
    return len(errors) == 0, errors

# ==========================================
# 2. اختبار الاستيرادات
# ==========================================
def test_imports():
    """اختبار استيراد الوحدات"""
    print("\n📋 [2/5] اختبار الاستيرادات...")
    
    errors = []
    
    # اختبار utils
    try:
        from utils import (
            get_scholar_link_cached,
            save_support_ticket_optimized,
            create_fancy_download_button_optimized,
            format_file_size
        )
        print("   ✅ utils.py - جميع الدوال موجودة")
    except ImportError as e:
        print(f"   ❌ utils.py: {e}")
        errors.append(("utils.py", str(e)))
    
    # اختبار processor
    try:
        from processor_optimized import OptimizedDocumentProcessor
        print("   ✅ processor_optimized.py - OptimizedDocumentProcessor موجود")
    except ImportError as e:
        print(f"   ❌ processor_optimized.py: {e}")
        errors.append(("processor_optimized.py", str(e)))
    
    # اختبار engine
    try:
        from engine_optimized import OptimizedRAGEngine, PerformanceMonitor
        print("   ✅ engine_optimized.py - OptimizedRAGEngine موجود")
    except ImportError as e:
        print(f"   ❌ engine_optimized.py: {e}")
        errors.append(("engine_optimized.py", str(e)))
    
    return len(errors) == 0, errors

# ==========================================
# 3. اختبار Utils Functions
# ==========================================
def test_utils_functions():
    """اختبار دوال utils"""
    print("\n📋 [3/5] اختبار دوال utils...")
    
    errors = []
    
    try:
        from utils import get_scholar_link_cached
        
        # اختبار get_scholar_link_cached
        result = get_scholar_link_cached("test_paper.pdf")
        assert "scholar.google.com" in result, "الرابط يجب أن يحتوي على scholar.google.com"
        print("   ✅ get_scholar_link_cached يعمل بشكل صحيح")
        
    except Exception as e:
        print(f"   ❌ get_scholar_link_cached: {e}")
        errors.append(("get_scholar_link_cached", str(e)))
    
    try:
        from utils import format_file_size
        
        # اختبار format_file_size
        assert format_file_size(1024) == "1.00 KB", "يجب أن يكون 1.00 KB"
        assert "MB" in format_file_size(1024 * 1024), "يجب أن يحتوي على MB"
        assert "GB" in format_file_size(1024 * 1024 * 1024), "يجب أن يحتوي على GB"
        print("   ✅ format_file_size يعمل بشكل صحيح")
        
    except Exception as e:
        print(f"   ❌ format_file_size: {e}")
        errors.append(("format_file_size", str(e)))
    
    try:
        from utils import sanitize_filename
        
        # اختبار sanitize_filename
        result = sanitize_filename("test<file>name.pdf")
        assert "<" not in result and ">" not in result, "يجب إزالة الرموز غير المسموحة"
        print("   ✅ sanitize_filename يعمل بشكل صحيح")
        
    except Exception as e:
        print(f"   ❌ sanitize_filename: {e}")
        errors.append(("sanitize_filename", str(e)))
    
    return len(errors) == 0, errors

# ==========================================
# 4. اختبار Classes
# ==========================================
def test_classes():
    """اختبار الـ Classes"""
    print("\n📋 [4/5] اختبار الـ Classes...")
    
    errors = []
    
    # اختبار PerformanceMonitor
    try:
        from engine_optimized import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        monitor.start_timer('test')
        monitor.stop_timer('test')
        
        assert 'metrics' in dir(monitor), "يجب أن يحتوي على metrics"
        print("   ✅ PerformanceMonitor يعمل بشكل صحيح")
        
    except Exception as e:
        print(f"   ❌ PerformanceMonitor: {e}")
        errors.append(("PerformanceMonitor", str(e)))
    
    # اختبار SmartCache
    try:
        from utils import SmartCache
        
        cache = SmartCache(max_size=10)
        cache.set("key1", "value1")
        result = cache.get("key1")
        
        assert result == "value1", "يجب أن يرجع القيمة المخزنة"
        print("   ✅ SmartCache يعمل بشكل صحيح")
        
    except Exception as e:
        print(f"   ❌ SmartCache: {e}")
        errors.append(("SmartCache", str(e)))
    
    # اختبار OptimizedDocumentProcessor
    try:
        from processor_optimized import OptimizedDocumentProcessor
        
        processor = OptimizedDocumentProcessor(chunk_size=1000, chunk_overlap=100)
        
        assert hasattr(processor, 'text_splitter'), "يجب أن يحتوي على text_splitter"
        assert hasattr(processor, 'process_single_pdf'), "يجب أن يحتوي على process_single_pdf"
        print("   ✅ OptimizedDocumentProcessor يمكن إنشاؤه بشكل صحيح")
        
    except Exception as e:
        print(f"   ❌ OptimizedDocumentProcessor: {e}")
        errors.append(("OptimizedDocumentProcessor", str(e)))
    
    return len(errors) == 0, errors

# ==========================================
# 5. اختبار Engine Methods
# ==========================================
def test_engine_methods():
    """اختبار وجود جميع methods في OptimizedRAGEngine"""
    print("\n📋 [5/5] اختبار methods في OptimizedRAGEngine...")
    
    errors = []
    
    try:
        from engine_optimized import OptimizedRAGEngine
        
        # الـ methods المطلوبة من app_optimized.py
        required_methods = [
            'get_vectorstore',
            'get_document_count',
            'ingest_documents_bulk',
            'clear_database',
            'query_with_cache',
            'get_optimized_chain',
            'generate_research_summary_optimized',
            'get_system_stats',
            'get_indexed_files'
        ]
        
        # التحقق من وجود جميع الـ methods
        for method in required_methods:
            if hasattr(OptimizedRAGEngine, method):
                print(f"   ✅ {method} موجود")
            else:
                print(f"   ❌ {method} غير موجود!")
                errors.append((method, "Method غير موجود"))
        
        # التحقق من الـ properties
        required_properties = ['embeddings', 'llm']
        for prop in required_properties:
            if prop in [p for p in dir(OptimizedRAGEngine) if not p.startswith('_')]:
                print(f"   ✅ {prop} property موجود")
            else:
                print(f"   ⚠️ {prop} property (قد يكون private)")
        
        # التحقق من الـ attributes في __init__
        required_attrs = [
            '_query_cache',
            '_metadata_cache',
            'monitor',
            'stats'
        ]
        
        # يمكننا التحقق بشكل غير مباشر عن طريق فحص الكود
        import inspect
        source = inspect.getsource(OptimizedRAGEngine.__init__)
        
        for attr in required_attrs:
            if attr in source:
                print(f"   ✅ {attr} معرف في __init__")
            else:
                print(f"   ❌ {attr} غير معرف في __init__!")
                errors.append((attr, "غير معرف في __init__"))
        
    except Exception as e:
        print(f"   ❌ خطأ عام: {e}")
        errors.append(("Engine", str(e)))
    
    return len(errors) == 0, errors

# ==========================================
# تشغيل جميع الاختبارات
# ==========================================
def run_all_tests():
    """تشغيل جميع الاختبارات"""
    results = []
    
    # 1. Syntax
    success, errors = test_syntax()
    results.append(("Syntax", success, errors))
    
    # 2. Imports
    success, errors = test_imports()
    results.append(("Imports", success, errors))
    
    # 3. Utils
    success, errors = test_utils_functions()
    results.append(("Utils Functions", success, errors))
    
    # 4. Classes
    success, errors = test_classes()
    results.append(("Classes", success, errors))
    
    # 5. Engine Methods
    success, errors = test_engine_methods()
    results.append(("Engine Methods", success, errors))
    
    # ==========================================
    # ملخص النتائج
    # ==========================================
    print("\n" + "=" * 60)
    print("📊 ملخص نتائج الاختبار")
    print("=" * 60)
    
    total_passed = sum(1 for _, success, _ in results if success)
    total_tests = len(results)
    
    for name, success, errors in results:
        status = "✅" if success else "❌"
        print(f"   {status} {name}")
    
    print("\n" + "-" * 40)
    print(f"   النتيجة: {total_passed}/{total_tests} اختبارات ناجحة")
    
    if total_passed == total_tests:
        print("\n🎉 جميع الاختبارات ناجحة! الكود جاهز للاستخدام.")
    else:
        print("\n⚠️ يوجد بعض المشاكل التي تحتاج إصلاح:")
        for name, success, errors in results:
            if not success:
                for error_name, error_msg in errors:
                    print(f"   • {name}/{error_name}: {error_msg}")
    
    print("\n" + "=" * 60)
    
    return total_passed == total_tests

# ==========================================
# نقطة الدخول
# ==========================================
if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
