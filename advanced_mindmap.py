 # advanced_mindmap.py
"""
مولد خرائط ذهنية متقدم مع تصور تفاعلي وتصدير
✨ يدعم: markmap.js (الأفضل) + D3.js Radial + Plotly
"""

import json
import re
from typing import Dict, List, Optional, Tuple
import uuid
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components

# ─── Visualization libraries ───────────────────────────────────────────────
try:
    import plotly.graph_objects as go
    import networkx as nx
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ─── streamlit-markmap ─────────────────────────────────────────────────────
try:
    from streamlit_markmap import markmap
    MARKMAP_AVAILABLE = True
except ImportError:
    MARKMAP_AVAILABLE = False

# ─── streamlit-agraph ──────────────────────────────────────────────────────
try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

# Import the prompts library
from intelligent_prompts_library import IntelligentPromptsLibrary, AnalysisType


class AdvancedMindMapGenerator:
    """مولد خرائط ذهنية احترافي"""
    
    def __init__(self, llm, language: str = "ar"):
        """
        Args:
            llm: نموذج اللغة الكبير (LLM)
            language: اللغة الافتراضية
        """
        self.llm = llm
        self.language = language
        self.prompts_library = IntelligentPromptsLibrary(language=language)
        self.last_mindmap = None
    
    def generate_mindmap(
        self,
        text: str,
        depth: int = 4,
        min_nodes: int = 15,
        language: Optional[str] = None
    ) -> Dict:
        """
        توليد خريطة ذهنية شاملة
        
        Args:
            text: النص المراد تحليله
            depth: عمق المستويات (2-5)
            min_nodes: الحد الأدنى للعقد
            language: اللغة (None = auto-detect)
        
        Returns:
            بيانات الخريطة الذهنية بصيغة JSON
        """
        # Auto-detect language if not specified
        if language is None:
            language = self.prompts_library.detect_language(text)
        
        # تقسيم النص إلى chunks إذا كان طويلاً
        chunks = self._smart_chunk(text, max_size=7000)
        
        mindmaps = []
        for chunk in chunks:
            # توليد الـ prompt
            prompt = self.prompts_library.get_mindmap_generation_prompt(
                text=chunk,
                language=language,
                depth=depth,
                min_nodes=min_nodes
            )
            
            # استدعاء LLM
            response = self.llm.invoke(prompt)
            
            # استخراج JSON من الاستجابة
            mindmap = self._extract_json_from_response(response)
            
            if mindmap:
                # تطبيع البيانات
                mindmap = self._normalize_mindmap_data(mindmap)
                mindmaps.append(mindmap)
        
        # دمج الخرائط إذا كان هناك أكثر من chunk
        if len(mindmaps) > 1:
            final_mindmap = self._merge_mindmaps(mindmaps)
        elif len(mindmaps) == 1:
            final_mindmap = mindmaps[0]
        else:
            # Fallback: إذا فشل LLM، استخدم استخراج بسيط
            final_mindmap = self._extract_simple_mindmap(text, min_nodes)
        
        # التحقق من الجودة
        final_mindmap = self._validate_and_enhance_mindmap(
            final_mindmap,
            min_nodes=min_nodes,
            depth=depth
        )
        
        # حفظ آخر خريطة
        self.last_mindmap = final_mindmap
        
        return final_mindmap
    
    def _smart_chunk(self, text: str, max_size: int = 7000) -> List[str]:
        """
        تقسيم ذكي للنص
        
        Args:
            text: النص المراد تقسيمه
            max_size: الحجم الأقصى لكل chunk
        
        Returns:
            قائمة من chunks
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) <= max_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text[:max_size]]
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """استخراج JSON من استجابة LLM"""
        try:
            # محاولة 1: JSON مباشر
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            pass
        
        try:
            # محاولة 2: استخراج من markdown code block
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                return data
        except json.JSONDecodeError:
            pass
        
        try:
            # محاولة 3: استخراج أول كائن JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _normalize_mindmap_data(self, mindmap: Dict) -> Dict:
        """
        تطبيع بيانات الخريطة الذهنية لضمان التنسيق الصحيح
        """
        normalized = {
            "central_topic": {},
            "main_branches": [],
            "sub_branches": [],
            "relationships": [],
            "metadata": {}
        }
        
        # Central topic
        if isinstance(mindmap.get("central_topic"), dict):
            normalized["central_topic"] = mindmap["central_topic"]
        elif isinstance(mindmap.get("central_topic"), str):
            normalized["central_topic"] = {
                "id": "central",
                "text": mindmap["central_topic"]
            }
        
        # Main branches
        main_concepts = mindmap.get("main_concepts", []) or mindmap.get("main_branches", [])
        for concept in main_concepts:
            if isinstance(concept, dict):
                # إضافة ID إذا لم يكن موجوداً
                if "id" not in concept:
                    concept["id"] = str(uuid.uuid4())[:8]
                normalized["main_branches"].append(concept)
        
        # Sub branches
        sub_concepts = mindmap.get("sub_branches", [])
        for sub in sub_concepts:
            if isinstance(sub, dict):
                if "id" not in sub:
                    sub["id"] = str(uuid.uuid4())[:8]
                normalized["sub_branches"].append(sub)
        
        # Extract sub-concepts from main concepts
        for main in normalized["main_branches"]:
            if "sub_concepts" in main and isinstance(main["sub_concepts"], list):
                for sub in main["sub_concepts"]:
                    if isinstance(sub, dict):
                        if "id" not in sub:
                            sub["id"] = str(uuid.uuid4())[:8]
                        if "parent_id" not in sub:
                            sub["parent_id"] = main["id"]
                        normalized["sub_branches"].append(sub)
                    elif isinstance(sub, str):
                        normalized["sub_branches"].append({
                            "id": str(uuid.uuid4())[:8],
                            "name": sub,
                            "parent_id": main["id"],
                            "level": 2
                        })
        
        # Relationships
        relationships = mindmap.get("relationships", [])
        for rel in relationships:
            if isinstance(rel, dict):
                normalized["relationships"].append(rel)
        
        # Metadata
        normalized["metadata"] = mindmap.get("metadata", {})
        
        return normalized
    
    def _merge_mindmaps(self, mindmaps: List[Dict]) -> Dict:
        """دمج عدة خرائط ذهنية في واحدة"""
        if not mindmaps:
            return {}
        
        merged = {
            "central_topic": mindmaps[0]["central_topic"],
            "main_branches": [],
            "sub_branches": [],
            "relationships": [],
            "metadata": {}
        }
        
        # دمج الفروع الرئيسية (تجنب التكرار)
        seen_names = set()
        for mm in mindmaps:
            for branch in mm.get("main_branches", []):
                name = branch.get("name") or branch.get("concept", "")
                if name and name not in seen_names:
                    merged["main_branches"].append(branch)
                    seen_names.add(name)
        
        # دمج الفروع الفرعية
        for mm in mindmaps:
            merged["sub_branches"].extend(mm.get("sub_branches", []))
        
        # دمج العلاقات
        for mm in mindmaps:
            merged["relationships"].extend(mm.get("relationships", []))
        
        # دمج metadata
        for mm in mindmaps:
            merged["metadata"].update(mm.get("metadata", {}))
        
        return merged
    
    def _extract_simple_mindmap(self, text: str, min_nodes: int = 15) -> Dict:
        """
        استخراج خريطة ذهنية بسيطة كـ fallback
        """
        from collections import Counter
        
        # استخراج الكلمات
        words = [word for word in text.split() if len(word) > 3]
        word_freq = Counter(words)
        top_keywords = [word for word, freq in word_freq.most_common(min_nodes * 2)]
        
        # إنشاء خريطة بسيطة
        mindmap = {
            "central_topic": {
                "id": "central",
                "text": "الموضوع الرئيسي"
            },
            "main_branches": [],
            "sub_branches": [],
            "relationships": [],
            "metadata": {
                "keywords": top_keywords[:30],
                "extraction_method": "simple_fallback"
            }
        }
        
        # إنشاء فروع رئيسية
        for i, keyword in enumerate(top_keywords[:min(8, min_nodes)]):
            branch_id = f"main_{i}"
            mindmap["main_branches"].append({
                "id": branch_id,
                "name": keyword,
                "concept": keyword,
                "importance_score": 1.0 - (i * 0.1),
                "category": "مفهوم"
            })
            
            # إضافة فروع فرعية
            for j in range(2):
                sub_idx = i * 2 + j
                if sub_idx < len(top_keywords):
                    mindmap["sub_branches"].append({
                        "id": f"sub_{i}_{j}",
                        "name": top_keywords[sub_idx],
                        "parent_id": branch_id,
                        "level": 2
                    })
        
        return mindmap
    
    def _validate_and_enhance_mindmap(
        self,
        mindmap: Dict,
        min_nodes: int = 15,
        depth: int = 4
    ) -> Dict:
        """
        التحقق من جودة الخريطة وتحسينها
        """
        # Count total nodes
        total_nodes = (
            len(mindmap.get("main_branches", [])) +
            len(mindmap.get("sub_branches", []))
        )
        
        # إذا كان عدد العقد قليل، أضف المزيد
        if total_nodes < min_nodes:
            # استخراج المزيد من keywords
            keywords = mindmap.get("metadata", {}).get("keywords", [])
            existing_names = set(
                [b.get("name") or b.get("concept", "") for b in mindmap.get("main_branches", [])]
            )
            
            # إضافة فروع إضافية من keywords
            for keyword in keywords:
                if keyword not in existing_names and len(mindmap["main_branches"]) < min_nodes:
                    mindmap["main_branches"].append({
                        "id": str(uuid.uuid4())[:8],
                        "name": keyword,
                        "concept": keyword,
                        "importance_score": 0.5,
                        "category": "مفهوم إضافي"
                    })
        
        # التأكد من وجود IDs فريدة
        self._ensure_unique_ids(mindmap)
        
        # إضافة علاقات إضافية إذا كانت قليلة
        if len(mindmap.get("relationships", [])) < total_nodes // 3:
            mindmap["relationships"] = self._generate_automatic_relationships(mindmap)
        
        return mindmap
    
    def _ensure_unique_ids(self, mindmap: Dict):
        """التأكد من أن جميع العقد لها IDs فريدة"""
        seen_ids = set()
        
        for branch in mindmap.get("main_branches", []):
            if "id" not in branch or branch["id"] in seen_ids:
                branch["id"] = str(uuid.uuid4())[:8]
            seen_ids.add(branch["id"])
        
        for sub in mindmap.get("sub_branches", []):
            if "id" not in sub or sub["id"] in seen_ids:
                sub["id"] = str(uuid.uuid4())[:8]
            seen_ids.add(sub["id"])
    
    def _generate_automatic_relationships(self, mindmap: Dict) -> List[Dict]:
        """توليد علاقات تلقائية بناءً على البنية"""
        relationships = []
        
        # علاقة المركز بالفروع الرئيسية
        central_id = mindmap.get("central_topic", {}).get("id", "central")
        for branch in mindmap.get("main_branches", []):
            relationships.append({
                "source_id": central_id,
                "target_id": branch["id"],
                "relationship_type": "جزء_من",
                "strength": 1.0,
                "description": "فرع رئيسي"
            })
        
        # علاقة الفروع الرئيسية بالفرعية
        for sub in mindmap.get("sub_branches", []):
            if "parent_id" in sub:
                relationships.append({
                    "source_id": sub["parent_id"],
                    "target_id": sub["id"],
                    "relationship_type": "يحتوي_على",
                    "strength": 0.8,
                    "description": "فرع فرعي"
                })
        
        return relationships
    
    # ═══════════════════════════════════════════════════════════════
    # Visualization Methods
    # ═══════════════════════════════════════════════════════════════
    
    def visualize_interactive(
        self,
        mindmap: Optional[Dict] = None,
        layout: str = "hierarchical"
    ) -> Optional[go.Figure]:
        """
        تصور تفاعلي للخريطة الذهنية
        
        Args:
            mindmap: بيانات الخريطة (None = استخدم آخر خريطة)
            layout: نوع التخطيط ("hierarchical", "radial", "force")
        
        Returns:
            Plotly figure
        """
        if not PLOTLY_AVAILABLE:
            raise ImportError("Plotly is required for visualization")
        
        if mindmap is None:
            mindmap = self.last_mindmap
        
        if not mindmap:
            return None
        
        # إنشاء graph
        G = self._build_networkx_graph(mindmap)
        
        # اختيار layout
        if layout == "hierarchical":
            pos = nx.spring_layout(G, k=2, iterations=50)
        elif layout == "radial":
            pos = nx.circular_layout(G)
        else:
            pos = nx.spring_layout(G)
        
        # استخراج بيانات العقد
        node_data = self._extract_node_visualization_data(G, pos, mindmap)
        
        # استخراج بيانات الحواف
        edge_data = self._extract_edge_visualization_data(G, pos)
        
        # إنشاء Figure
        fig = go.Figure()
        
        # إضافة الحواف
        fig.add_trace(go.Scatter(
            x=edge_data["x"],
            y=edge_data["y"],
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines',
            showlegend=False
        ))
        
        # إضافة العقد
        fig.add_trace(go.Scatter(
            x=node_data["x"],
            y=node_data["y"],
            mode='markers+text',
            text=node_data["labels"],
            textposition="top center",
            marker=dict(
                color=node_data["colors"],
                size=node_data["sizes"],
                line=dict(width=2, color='white')
            ),
            hovertext=node_data["hover_text"],
            hoverinfo='text',
            showlegend=False
        ))
        
        # تحديث layout
        fig.update_layout(
            title="خريطة ذهنية تفاعلية",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=20, r=20, t=60),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            height=700
        )
        
        return fig
    
    def _build_networkx_graph(self, mindmap: Dict) -> nx.Graph:
        """بناء graph من بيانات الخريطة"""
        G = nx.Graph()
        
        # إضافة العقدة المركزية
        central = mindmap.get("central_topic", {})
        G.add_node(
            central.get("id", "central"),
            label=central.get("text", "المركز"),
            node_type="central",
            size=40,
            color='#FF6B6B'
        )
        
        # إضافة الفروع الرئيسية
        for branch in mindmap.get("main_branches", []):
            node_id = branch.get("id")
            G.add_node(
                node_id,
                label=branch.get("name") or branch.get("concept", ""),
                node_type="main",
                size=25,
                color='#4ECDC4',
                importance=branch.get("importance_score", 0.5)
            )
            # ربط بالمركز
            G.add_edge(central.get("id", "central"), node_id, weight=1.0)
        
        # إضافة الفروع الفرعية
        for sub in mindmap.get("sub_branches", []):
            node_id = sub.get("id")
            parent_id = sub.get("parent_id")
            G.add_node(
                node_id,
                label=sub.get("name") or sub.get("concept", ""),
                node_type="sub",
                size=15,
                color='#FFD166',
                level=sub.get("level", 2)
            )
            if parent_id and parent_id in G.nodes():
                G.add_edge(parent_id, node_id, weight=0.7)
        
        # إضافة علاقات إضافية
        for rel in mindmap.get("relationships", []):
            source = rel.get("source_id")
            target = rel.get("target_id")
            if source in G.nodes() and target in G.nodes():
                strength = rel.get("strength", 0.5)
                G.add_edge(source, target, weight=strength)
        
        return G
    
    def _extract_node_visualization_data(
        self,
        G: nx.Graph,
        pos: Dict,
        mindmap: Dict
    ) -> Dict:
        """استخراج بيانات العقد للتصور"""
        node_x, node_y = [], []
        node_labels, node_colors, node_sizes = [], [], []
        hover_texts = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            attrs = G.nodes[node]
            node_labels.append(attrs.get("label", ""))
            node_colors.append(attrs.get("color", "#999"))
            node_sizes.append(attrs.get("size", 15))
            
            # Hover text
            hover = f"<b>{attrs.get('label', '')}</b><br>"
            hover += f"النوع: {attrs.get('node_type', 'unknown')}<br>"
            if "importance" in attrs:
                hover += f"الأهمية: {attrs['importance']:.2f}"
            hover_texts.append(hover)
        
        return {
            "x": node_x,
            "y": node_y,
            "labels": node_labels,
            "colors": node_colors,
            "sizes": node_sizes,
            "hover_text": hover_texts
        }
    
    def _extract_edge_visualization_data(
        self,
        G: nx.Graph,
        pos: Dict
    ) -> Dict:
        """استخراج بيانات الحواف للتصور"""
        edge_x, edge_y = [], []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        return {"x": edge_x, "y": edge_y}
    
    # ═══════════════════════════════════════════════════════════════
    # Export Methods
    # ═══════════════════════════════════════════════════════════════
    
    def export_json(self, mindmap: Optional[Dict] = None) -> str:
        """تصدير الخريطة بصيغة JSON"""
        if mindmap is None:
            mindmap = self.last_mindmap
        
        return json.dumps(mindmap, ensure_ascii=False, indent=2)
    
    def export_mermaid(self, mindmap: Optional[Dict] = None) -> str:
        """
        تصدير الخريطة بصيغة Mermaid (للتضمين في markdown)
        """
        if mindmap is None:
            mindmap = self.last_mindmap
        
        if not mindmap:
            return ""
        
        mermaid = "graph TD\n"
        
        # Central topic
        central = mindmap.get("central_topic", {})
        central_id = central.get("id", "C")
        central_text = central.get("text", "المركز")
        mermaid += f"    {central_id}[{central_text}]\n"
        
        # Main branches
        for branch in mindmap.get("main_branches", []):
            branch_id = branch.get("id", "")
            branch_name = branch.get("name") or branch.get("concept", "")
            mermaid += f"    {branch_id}({branch_name})\n"
            mermaid += f"    {central_id} --> {branch_id}\n"
        
        # Sub branches
        for sub in mindmap.get("sub_branches", []):
            sub_id = sub.get("id", "")
            sub_name = sub.get("name") or sub.get("concept", "")
            parent_id = sub.get("parent_id", "")
            mermaid += f"    {sub_id}[{sub_name}]\n"
            if parent_id:
                mermaid += f"    {parent_id} --> {sub_id}\n"
        
        return mermaid
    
    def export_text_outline(self, mindmap: Optional[Dict] = None) -> str:
        """تصدير الخريطة كمخطط نصي"""
        if mindmap is None:
            mindmap = self.last_mindmap
        
        if not mindmap:
            return ""
        
        outline = f"# {mindmap.get('central_topic', {}).get('text', 'خريطة ذهنية')}\n\n"
        
        # Main branches
        for i, branch in enumerate(mindmap.get("main_branches", []), 1):
            branch_name = branch.get("name") or branch.get("concept", "")
            outline += f"## {i}. {branch_name}\n"
            
            # Find sub-branches
            branch_id = branch.get("id")
            subs = [
                sub for sub in mindmap.get("sub_branches", [])
                if sub.get("parent_id") == branch_id
            ]
            
            for j, sub in enumerate(subs, 1):
                sub_name = sub.get("name") or sub.get("concept", "")
                outline += f"   {i}.{j}. {sub_name}\n"
            
            outline += "\n"
        
        # Metadata
        metadata = mindmap.get("metadata", {})
        if metadata.get("keywords"):
            outline += "## الكلمات المفتاحية\n"
            outline += ", ".join(metadata["keywords"][:20])
            outline += "\n"
        
        return outline

    # ═══════════════════════════════════════════════════════════════
    # 🌟 markmap.js - أفضل مكتبة للخرائط الذهنية
    # ═══════════════════════════════════════════════════════════════

    def generate_markmap_markdown(self, mindmap: Optional[Dict] = None) -> str:
        """
        تحويل بيانات الخريطة إلى Markdown هرمي متوافق مع markmap.js
        
        markmap.js تعرض هذا الـ Markdown كخريطة ذهنية تفاعلية:
        - زوم وتحريك
        - طي وتوسيع الفروع
        - ألوان تلقائية جميلة
        """
        if mindmap is None:
            mindmap = self.last_mindmap
        
        if not mindmap:
            return ""
        
        central = mindmap.get("central_topic", {})
        central_text = central.get("text", "الخريطة الذهنية")
        
        md_lines = [f"# {central_text}"]
        
        # الفروع الرئيسية
        main_branches = mindmap.get("main_branches", [])
        for branch in main_branches:
            branch_name = branch.get("name") or branch.get("concept", "")
            if not branch_name:
                continue
            md_lines.append(f"## {branch_name}")
            
            # إضافة وصف إن وجد
            desc = branch.get("description") or branch.get("explanation", "")
            if desc and len(desc) > 5:
                md_lines.append(f"### 📝 {desc[:80]}")
            
            # الفروع الفرعية المرتبطة بهذا الفرع
            branch_id = branch.get("id", "")
            sub_items = branch.get("sub_concepts", []) or branch.get("sub_topics", []) or []
            
            # أيضاً ابحث في sub_branches العامة
            for sub in mindmap.get("sub_branches", []):
                if sub.get("parent_id") == branch_id:
                    sub_items.append(sub)
            
            for sub in sub_items:
                if isinstance(sub, str):
                    md_lines.append(f"### {sub}")
                elif isinstance(sub, dict):
                    sub_name = sub.get("name") or sub.get("concept", "")
                    if sub_name:
                        md_lines.append(f"### {sub_name}")
                        # فروع من المستوى الثالث
                        details = sub.get("details") or sub.get("key_points", [])
                        if isinstance(details, list):
                            for d in details[:3]:
                                if isinstance(d, str) and d.strip():
                                    md_lines.append(f"#### {d}")
                        elif isinstance(details, str) and details.strip():
                            md_lines.append(f"#### {details[:60]}")
        
        # الكلمات المفتاحية كفرع إضافي
        keywords = mindmap.get("metadata", {}).get("keywords", [])
        if keywords:
            md_lines.append("## 🔑 الكلمات المفتاحية")
            for kw in keywords[:8]:
                md_lines.append(f"### {kw}")
        
        return "\n".join(md_lines)

    def render_with_markmap(
        self,
        mindmap: Optional[Dict] = None,
        height: int = 550
    ):
        """
        عرض الخريطة الذهنية باستخدام markmap.js في Streamlit
        أفضل مكتبة: تفاعلية، جميلة، تدعم العربية والإنجليزية
        """
        if mindmap is None:
            mindmap = self.last_mindmap
        
        if not mindmap:
            st.error("❌ لا توجد بيانات خريطة ذهنية")
            return
        
        md_content = self.generate_markmap_markdown(mindmap)
        
        if MARKMAP_AVAILABLE:
            markmap(md_content, height=height)
        else:
            # Fallback: عرض HTML مباشر باستخدام markmap CDN
            self._render_markmap_via_cdn(md_content, height)

    def _render_markmap_via_cdn(self, md_content: str, height: int = 550):
        """
        عرض markmap عبر CDN كـ fallback إذا لم تكن المكتبة مثبتة
        """
        escaped_md = json.dumps(md_content)
        html = f"""
<!DOCTYPE html>
<html dir="auto">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ margin: 0; background: #0f1117; }}
    #mindmap {{ width: 100%; height: {height}px; }}
    .markmap-node circle {{ cursor: pointer; }}
    .markmap-node text {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }}
  </style>
</head>
<body>
  <svg id="mindmap"></svg>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.17"></script>
  <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.17"></script>
  <script>
    const {{ Transformer, Markmap }} = window.markmap;
    const transformer = new Transformer();
    const md = {escaped_md};
    const {{ root, features }} = transformer.transform(md);
    const mm = Markmap.create('#mindmap', {{
      initialExpandLevel: 3,
      colorFreezeLevel: 2,
      duration: 500,
      fitRatio: 0.95,
    }});
    mm.setData(root);
    setTimeout(() => mm.fit(), 300);
  </script>
</body>
</html>
"""
        components.html(html, height=height)

    # ═══════════════════════════════════════════════════════════════
    # 🎨 D3.js - تصور احترافي بالشجرة الدائرية
    # ═══════════════════════════════════════════════════════════════

    def generate_d3_html(self, mindmap: Optional[Dict] = None, height: int = 650) -> str:
        """
        توليد HTML كامل يعرض الخريطة كـ D3.js Collapsible Radial Tree
        أحدث تصور احترافي مثل AI Mind Maps Maker
        """
        if mindmap is None:
            mindmap = self.last_mindmap
        
        if not mindmap:
            return ""
        
        # بناء بيانات D3 hierarchy
        tree_data = self._build_d3_tree(mindmap)
        tree_json = json.dumps(tree_data, ensure_ascii=False)
        
        html = f"""
<!DOCTYPE html>
<html dir="auto">
<head>
  <meta charset="UTF-8">
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #0f1117; font-family: 'Segoe UI', Arial, sans-serif; }}
    #chart-container {{
      width: 100%; height: {height}px;
      display: flex; align-items: center; justify-content: center;
    }}
    .node circle {{
      stroke-width: 2.5;
      cursor: pointer;
      transition: r 0.3s, filter 0.3s;
      filter: drop-shadow(0 0 4px rgba(99,179,237,0.4));
    }}
    .node circle:hover {{
      filter: drop-shadow(0 0 10px rgba(99,179,237,0.9));
    }}
    .node text {{
      font-size: 11px;
      fill: #e2e8f0;
      cursor: pointer;
      text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    }}
    .link {{
      fill: none;
      stroke-width: 1.5;
      opacity: 0.7;
    }}
    .tooltip {{
      position: absolute;
      background: rgba(255,255,255,0.1);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(99,179,237,0.3);
      border-radius: 8px;
      padding: 8px 12px;
      color: #e2e8f0;
      font-size: 12px;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s;
      max-width: 200px;
    }}
    .legend {{
      position: absolute;
      top: 10px; right: 10px;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px; padding: 8px 12px;
      color: #a0aec0; font-size: 11px;
    }}
    .legend div {{ margin: 3px 0; display: flex; align-items: center; gap: 6px; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  </style>
</head>
<body>
  <div id="chart-container"><svg id="d3-mindmap"></svg></div>
  <div class="tooltip" id="tooltip"></div>
  <div class="legend">
    <div><span class="legend-dot" style="background:#FF6B6B"></span> الموضوع الرئيسي</div>
    <div><span class="legend-dot" style="background:#4ECDC4"></span> الفروع الرئيسية</div>
    <div><span class="legend-dot" style="background:#FFD166"></span> الفروع الفرعية</div>
    <div><span class="legend-dot" style="background:#A78BFA"></span> التفاصيل</div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script>
    const data = {tree_json};
    const W = document.getElementById('chart-container').offsetWidth || 800;
    const H = {height};
    const radius = Math.min(W, H) / 2 - 80;

    const COLORS = ['#FF6B6B','#4ECDC4','#FFD166','#A78BFA','#F687B3','#68D391','#63B3ED','#FC8181'];
    const colorScale = d3.scaleOrdinal(COLORS);

    const svg = d3.select('#d3-mindmap')
      .attr('width', W)
      .attr('height', H)
      .call(d3.zoom().scaleExtent([0.3,3]).on('zoom', (e) => g.attr('transform', e.transform)))
      .append('g');
    const g = svg.append('g').attr('transform', `translate(${{W/2}},${{H/2}})`);

    const tooltip = document.getElementById('tooltip');
    
    // gradient defs
    const defs = svg.append('defs');
    COLORS.forEach((c, i) => {{
      const grad = defs.append('radialGradient').attr('id', `grad${{i}}`);
      grad.append('stop').attr('offset','0%').attr('stop-color', d3.color(c).brighter(0.5));
      grad.append('stop').attr('offset','100%').attr('stop-color', c);
    }});

    const tree = d3.cluster().size([2 * Math.PI, radius]);
    const hierarchy = d3.hierarchy(data);
    tree(hierarchy);

    // Links with gradient stroke
    const linkGen = d3.linkRadial().angle(d => d.x).radius(d => d.y);
    g.selectAll('.link')
      .data(hierarchy.links())
      .join('path')
      .attr('class', 'link')
      .attr('d', linkGen)
      .attr('stroke', d => colorScale(d.target.depth))
      .attr('stroke-width', d => Math.max(1, 4 - d.target.depth));

    // Nodes
    const node = g.selectAll('.node')
      .data(hierarchy.descendants())
      .join('g')
      .attr('class', 'node')
      .attr('transform', d => `rotate(${{d.x * 180 / Math.PI - 90}}) translate(${{d.y}})`)
      .on('mouseover', (event, d) => {{
        tooltip.style.opacity = 1;
        tooltip.style.left = (event.pageX + 10) + 'px';
        tooltip.style.top = (event.pageY - 10) + 'px';
        tooltip.innerHTML = `<b>${{d.data.name}}</b>${{d.data.desc ? '<br>' + d.data.desc : ''}}`;
      }})
      .on('mouseout', () => tooltip.style.opacity = 0);

    node.append('circle')
      .attr('r', d => d.depth === 0 ? 22 : d.depth === 1 ? 14 : d.depth === 2 ? 9 : 5)
      .attr('fill', d => `url(#grad${{d.depth % COLORS.length}})`)
      .attr('stroke', d => colorScale(d.depth))
      .attr('stroke-width', 2);

    node.append('text')
      .attr('dy', '0.31em')
      .attr('x', d => d.x < Math.PI === !d.children ? 10 : -10)
      .attr('text-anchor', d => d.x < Math.PI === !d.children ? 'start' : 'end')
      .attr('transform', d => d.x >= Math.PI ? 'rotate(180)' : null)
      .text(d => d.data.name ? (d.data.name.length > 20 ? d.data.name.slice(0,18)+'…' : d.data.name) : '')
      .style('font-size', d => d.depth === 0 ? '14px' : d.depth === 1 ? '12px' : '10px')
      .style('font-weight', d => d.depth <= 1 ? 'bold' : 'normal');
  </script>
</body>
</html>
"""
        return html

    def _build_d3_tree(self, mindmap: Dict) -> Dict:
        """بناء بيانات D3 hierarchy من بيانات الخريطة الذهنية"""
        central = mindmap.get("central_topic", {})
        root = {
            "name": central.get("text", "الخريطة الذهنية"),
            "desc": central.get("description", ""),
            "children": []
        }
        
        for branch in mindmap.get("main_branches", []):
            branch_name = branch.get("name") or branch.get("concept", "")
            if not branch_name:
                continue
            
            branch_node = {
                "name": branch_name,
                "desc": branch.get("description") or branch.get("explanation", ""),
                "children": []
            }
            
            # الفروع الفرعية
            branch_id = branch.get("id", "")
            sub_items = list(branch.get("sub_concepts", []) or branch.get("sub_topics", []) or [])
            for sub in mindmap.get("sub_branches", []):
                if sub.get("parent_id") == branch_id:
                    sub_items.append(sub)
            
            for sub in sub_items:
                if isinstance(sub, str):
                    branch_node["children"].append({"name": sub, "desc": ""})
                elif isinstance(sub, dict):
                    sub_name = sub.get("name") or sub.get("concept", "")
                    if sub_name:
                        sub_node = {"name": sub_name, "desc": sub.get("description", "")}
                        # فروع المستوى الثالث
                        details = sub.get("details") or sub.get("key_points", [])
                        if isinstance(details, list) and details:
                            sub_node["children"] = [
                                {"name": d} for d in details[:3] if isinstance(d, str) and d.strip()
                            ]
                        branch_node["children"].append(sub_node)
            
            root["children"].append(branch_node)
        
        return root

    # ═══════════════════════════════════════════════════════════════
    # 🚀 الواجهة الموحدة - تعرض الخريطة بأفضل طريقة
    # ═══════════════════════════════════════════════════════════════

    def render_mindmap_streamlit(
        self,
        mindmap: Optional[Dict] = None,
        mode: str = "markmap",
        height: int = 550
    ):
        """
        الدالة الرئيسية لعرض الخريطة الذهنية في Streamlit
        
        Args:
            mindmap: بيانات الخريطة (None = آخر خريطة مولّدة)
            mode: "markmap" | "d3" | "plotly"
            height: ارتفاع الخريطة بالبكسل
        """
        if mindmap is None:
            mindmap = self.last_mindmap
        
        if not mindmap:
            st.warning("⚠️ لا توجد خريطة ذهنية للعرض. قم بتوليد خريطة أولاً.")
            return
        
        if mode == "markmap":
            self.render_with_markmap(mindmap, height=height)
        
        elif mode == "d3":
            html_content = self.generate_d3_html(mindmap, height=height)
            components.html(html_content, height=height)
        
        elif mode == "plotly" and PLOTLY_AVAILABLE:
            fig = self.visualize_interactive(mindmap)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        else:
            # fallback تلقائي
            if MARKMAP_AVAILABLE:
                self.render_with_markmap(mindmap, height=height)
            elif PLOTLY_AVAILABLE:
                fig = self.visualize_interactive(mindmap)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                html_content = self.generate_d3_html(mindmap, height=height)
                components.html(html_content, height=height)
