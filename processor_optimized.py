import tempfile
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import PyPDF2
from PIL import Image, ImageOps
import pytesseract
from pdf2image import convert_from_path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import streamlit as st
from functools import lru_cache

class OptimizedDocumentProcessor:
    def __init__(self, chunk_size=1200, chunk_overlap=100):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "!", "؟", "?", ".", " ", ""]
        )
        self.ocr_dpi = 150  
        self.max_workers = min(os.cpu_count() * 2, 8)
        
    @lru_cache(maxsize=100)
    def _get_tesseract_config(self, lang):
        config = '--oem 3 --psm 6'
        if lang == 'ara':
            config += ' -c preserve_interword_spaces=1'
        return config
    
    def _ocr_single_image_optimized(self, img, lang='ara'):
        """OCR محسن للعربية فقط - أسرع بكثير من ara+eng"""
        gray_img = ImageOps.grayscale(img)
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(gray_img)
        gray_img = enhancer.enhance(1.5)
        config = self._get_tesseract_config('ara')
        text = pytesseract.image_to_string(gray_img, lang=lang, config=config)
        return text
    
    def _has_selectable_text(self, pdf_path):
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                pages_to_check = min(max(3, total_pages // 5), 5)
                text = ""
                for i in range(pages_to_check):
                    extracted = pdf_reader.pages[i].extract_text()
                    if extracted: text += extracted
                return len(text.strip()) > 50
        except Exception:
            return False
    
    def _process_digital_pdf(self, file_path, file_name):
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            for doc in documents:
                doc.metadata.update({"source": file_name, "type": "Digital Text", "processing_method": "direct_extraction"})
            return documents
        except Exception as e:
            st.warning(f"فشل في معالجة PDF النصي: {e}")
            return []
    
    def _process_scanned_pdf(self, file_path, file_name):
        try:
            images = convert_from_path(file_path, dpi=self.ocr_dpi, thread_count=2, grayscale=True)
            with ThreadPoolExecutor(max_workers=min(len(images), self.max_workers)) as executor:
                batch_size = 8  # زيادة من 4 لتسريع OCR
                all_texts = []
                for i in range(0, len(images), batch_size):
                    batch = images[i:i+batch_size]
                    batch_results = list(executor.map(self._ocr_single_image_optimized, batch))
                    all_texts.extend(batch_results)
            full_text = "\n\n".join([f"## الصفحة {i+1}\n{text}" for i, text in enumerate(all_texts)])
            document = Document(page_content=full_text, metadata={"source": file_name, "type": "Scanned", "processing_method": "ocr", "total_pages": len(images)})
            return [document]
        except Exception as e:
            st.warning(f"فشل في معالجة PDF الممسوح: {e}")
            return []
    
    def process_single_pdf(self, uploaded_file, force_ocr=False):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
                
            if force_ocr:
                is_text_based = False
            else:
                is_text_based = self._has_selectable_text(tmp_path)
                
            pages = []  # قائمة نصوص الصفحات الفعلية
            
            if is_text_based:
                documents = self._process_digital_pdf(tmp_path, uploaded_file.name)
                raw_text = "".join([doc.page_content for doc in documents])
                
                # Smart OCR Fallback: فحص إذا كان النص المستخرج مشوهاً (طلاسم)
                garbled_chars = sum(1 for c in raw_text if c.isalpha() and not c.isascii() and not ('\u0600' <= c <= '\u06FF'))
                valid_chars = sum(1 for c in raw_text if (c.isascii() and c.isalpha()) or ('\u0600' <= c <= '\u06FF'))
                
                is_garbled = False
                if len(raw_text.strip()) > 50 and garbled_chars > valid_chars:
                    is_garbled = True
                    
                if is_garbled:
                    st.warning(f"⚠️ تم اكتشاف نص مشوه في الملف '{uploaded_file.name}'، جاري التحويل التلقائي للمعالجة بالـ OCR...")
                    documents = self._process_scanned_pdf(tmp_path, uploaded_file.name)
                    raw_text = documents[0].page_content if documents else ""
                    if raw_text:
                        import re
                        page_splits = re.split(r'## الصفحة \d+\n', raw_text)
                        pages = [p.strip() for p in page_splits if p.strip()]
                    used_ocr = True
                else:
                    pages = [doc.page_content for doc in documents if doc.page_content.strip()]
                    used_ocr = False
            else:
                documents = self._process_scanned_pdf(tmp_path, uploaded_file.name)
                raw_text = documents[0].page_content if documents else ""
                if raw_text:
                    import re
                    page_splits = re.split(r'## الصفحة \d+\n', raw_text)
                    pages = [p.strip() for p in page_splits if p.strip()]
                used_ocr = True
                
            chunks = self.text_splitter.split_documents(documents) if documents else []
            return chunks, raw_text, used_ocr, pages
        except Exception as e:
            st.error(f"خطأ في معالجة {uploaded_file.name}: {str(e)}")
            return [], "", False, []
        finally:
            if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)
    
    def process_batch_pdfs(self, uploaded_files, progress_callback=None, force_ocr=False):
        results = []
        with ThreadPoolExecutor(max_workers=min(4, len(uploaded_files))) as executor:
            total_files = len(uploaded_files)
            future_to_file = {executor.submit(self.process_single_pdf, file, force_ocr): (i, file) for i, file in enumerate(uploaded_files)}
            completed = 0
            for future in as_completed(future_to_file):
                file_idx, file = future_to_file[future]
                try:
                    chunks, raw_text, used_ocr, pages = future.result()
                    results.append({'file': file, 'chunks': chunks, 'raw_text': raw_text, 'used_ocr': used_ocr, 'pages': pages, 'index': file_idx})
                    completed += 1
                    if progress_callback: progress_callback(completed, total_files, file.name)
                except Exception as e:
                    st.error(f"فشل في معالجة {file.name}: {str(e)}")
        results.sort(key=lambda x: x['index'])
        return results