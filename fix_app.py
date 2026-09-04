import re

file_path = "d:\\ملف هايدي كامل\\شغل هايدي\\MySearchEngine\\app_optimized.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add get_file_content_safe function
helper_func = '''
def get_file_content_safe(filename: str) -> str:
    \"\"\"استرجاع محتوى الملف بأمان (من الذاكرة أو قاعدة البيانات بشكل كسلان)\"\"\"
    txt = st.session_state.last_full_text.get(filename, "")
    if not txt or txt.startswith("[ملف مفهرس"):
        if st.session_state.rag_engine and hasattr(st.session_state.rag_engine, 'get_document_text_from_db'):
            with st.spinner(f"جاري جلب محتوى الملف {filename} من قاعدة البيانات..."):
                txt = st.session_state.rag_engine.get_document_text_from_db(filename)
                if txt:
                    st.session_state.last_full_text[filename] = txt
                else:
                    return ""
    return txt

'''

# Insert after load_indexed_files_from_db definition ends (around line 167)
if 'def get_file_content_safe' not in content:
    content = content.replace('    return False    ', '    return False    \\n' + helper_func)

# 2. Replace all st.session_state.last_full_text.get(...) with get_file_content_safe
content = re.sub(
    r'st\.session_state\.last_full_text\.get\(([^,]+),\s*""\)',
    r'get_file_content_safe(\1)',
    content
)

# 3. Replace direct dictionary access in translation tab
content = re.sub(
    r'st\.session_state\.last_full_text\[([^\]]+)\]',
    r'get_file_content_safe(\1)',
    content
)

# 4. Remove the lines in Tab 1 that check for placeholder
to_remove = '''                    
                    # إذا كان الملف من قاعدة البيانات ولا يوجد نص
                    if not txt or txt.startswith("[ملف مفهرس"):
                        txt = f"تحليل الملف: {selected_analysis_file}"'''
if to_remove in content:
    content = content.replace(to_remove, '')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Modifications applied successfully!")
