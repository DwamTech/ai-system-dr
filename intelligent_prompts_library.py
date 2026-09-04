# intelligent_prompts_library.py
"""
مكتبة Prompts الذكية المتقدمة
تدعم العربية والإنجليزية واللغات الأخرى مع تحليل عميق ومهيكل
"""

import json
from typing import Dict, List, Optional, Union
from enum import Enum


class AnalysisType(Enum):
    """أنواع التحليل المدعومة"""
    RESEARCH_PAPER = "research_paper"
    POETRY_ANALYSIS = "poetry_analysis"
    MINDMAP = "mindmap"
    LINGUISTIC_ANALYSIS = "linguistic_analysis"
    RHETORICAL_ANALYSIS = "rhetorical_analysis"
    COMPARATIVE_STUDY = "comparative_study"
    LITERATURE_REVIEW = "literature_review"
    ANATOMICAL_VIEW = "anatomical_view"
    VISUAL_INFOGRAPHIC = "visual_infographic"
    DATA_VISUALIZATION = "data_visualization"
    MATHEMATICAL_DIAGRAM = "mathematical_diagram"


class IntelligentPromptsLibrary:
    """مكتبة Prompts ذكية متعددة اللغات"""
    
    def __init__(self, language: str = "ar"):
        """
        Args:
            language: اللغة الأساسية ("ar", "en", "fr", etc.)
        """
        self.language = language
        self.prompts_cache = {}
    
    # ═══════════════════════════════════════════════════════════════
    # 1. Research Paper Analysis (Arabic & English)
    # ═══════════════════════════════════════════════════════════════
    
    def get_research_paper_deep_analysis_prompt(
        self,
        text: str,
        language: str = "ar",
        analysis_depth: str = "deep"
    ) -> str:
        """
        Prompt متقدم لتحليل الأوراق العلمية بعمق
        
        Args:
            text: النص المراد تحليله
            language: اللغة
            analysis_depth: عمق التحليل ("quick", "medium", "deep")
        """
        
        if language == "ar":
            prompt_structure = {
                "task": "تحليل شامل للبحث العلمي",
                "analysis_type": "deep_research_analysis",
                "language": "Arabic",
                "instructions": {
                    "step_1_structure": {
                        "description": "استخرج البنية الكاملة للبحث",
                        "required_sections": [
                            "العنوان (مع ترجمة إنجليزية إن أمكن)",
                            "الملخص/Abstract",
                            "الكلمات المفتاحية",
                            "المقدمة والخلفية النظرية",
                            "مشكلة البحث وأهميته",
                            "الأهداف (كقائمة مرقمة)",
                            "الأسئلة البحثية/الفرضيات",
                            "المنهجية والأدوات المستخدمة",
                            "النتائج الرئيسية (بالتفصيل)",
                            "المناقشة والتفسير",
                            "التوصيات والبحوث المستقبلية",
                            "المراجع (عدها فقط)"
                        ]
                    },
                    "step_2_key_concepts": {
                        "description": "استخراج المفاهيم والكيانات",
                        "extract": {
                            "main_concepts": "15-25 مفهوم رئيسي",
                            "researchers": "أسماء الباحثين المذكورين",
                            "institutions": "المؤسسات والجامعات",
                            "theories": "النظريات المستخدمة",
                            "methodologies": "المناهج البحثية المطبقة",
                            "tools_software": "الأدوات والبرامج المستخدمة",
                            "datasets": "مجموعات البيانات",
                            "metrics": "المقاييس والمعايير المستخدمة"
                        }
                    },
                    "step_3_numerical_findings": {
                        "description": "استخراج جميع الأرقام والإحصائيات الهامة",
                        "format": [
                            {
                                "metric": "اسم المقياس",
                                "value": "القيمة الرقمية",
                                "unit": "الوحدة",
                                "context": "السياق",
                                "significance": "الأهمية"
                            }
                        ]
                    },
                    "step_4_contribution": {
                        "description": "تحديد الإسهامات والمساهمات",
                        "aspects": [
                            "الإضافة العلمية الجديدة",
                            "الفجوات التي يسدها البحث",
                            "التطبيقات العملية المحتملة",
                            "التأثير المتوقع على المجال"
                        ]
                    },
                    "step_5_critical_analysis": {
                        "description": "تقييم نقدي للبحث",
                        "evaluate": {
                            "strengths": "نقاط القوة (3-5 نقاط)",
                            "limitations": "نقاط الضعف أو القيود (3-5 نقاط)",
                            "methodology_quality": "جودة المنهجية (تقييم من 1-10)",
                            "novelty": "مستوى الجدة والابتكار (تقييم من 1-10)",
                            "clarity": "وضوح العرض والكتابة (تقييم من 1-10)"
                        }
                    },
                    "step_6_connections": {
                        "description": "ربط البحث بالسياق الأوسع",
                        "identify": {
                            "related_fields": "المجالات ذات الصلة",
                            "cited_papers": "الأبحاث المستشهد بها (أهمها)",
                            "future_directions": "الاتجاهات المستقبلية المقترحة"
                        }
                    }
                },
                "output_format": {
                    "structure": "JSON",
                    "required_keys": [
                        "title", "abstract", "keywords", "introduction",
                        "research_problem", "objectives", "research_questions",
                        "methodology", "results", "discussion", "recommendations",
                        "key_concepts", "numerical_findings", "contribution",
                        "critical_analysis", "connections", "metadata"
                    ],
                    "metadata": {
                        "language_detected": "لغة النص المكتشفة",
                        "document_type": "نوع المستند",
                        "estimated_pages": "عدد الصفحات المقدر",
                        "complexity_level": "مستوى التعقيد (مبتدئ/متوسط/متقدم)"
                    }
                },
                "quality_checks": [
                    "تأكد من عدم  تفويت أي قسم رئيسي",
                    "استخرج جميع الأرقام والإحصائيات",
                    "لا تتجاهل أي معلومة هامة",
                    "كن دقيقاً في نقل الأرقام",
                    "حافظ على الأمانة العلمية"
                ]
            }
        else:  # English
            prompt_structure = {
                "task": "Comprehensive Research Paper Analysis",
                "analysis_type": "deep_research_analysis",
                "language": "English",
                "instructions": {
                    "step_1_structure": {
                        "description": "Extract the complete structure of the research",
                        "required_sections": [
                            "Title (with Arabic translation if possible)",
                            "Abstract",
                            "Keywords",
                            "Introduction & Theoretical Background",
                            "Research Problem & Significance",
                            "Objectives (as numbered list)",
                            "Research Questions/Hypotheses",
                            "Methodology & Tools",
                            "Main Results (detailed)",
                            "Discussion & Interpretation",
                            "Recommendations & Future Research",
                            "References (count only)"
                        ]
                    },
                    # Similar structure to Arabic but in English
                    "step_2_key_concepts": {
                        "extract": {
                            "main_concepts": "15-25 main concepts",
                            "researchers": "Researchers mentioned",
                            "institutions": "Institutions and universities",
                            "theories": "Theories used",
                            "methodologies": "Research methods applied",
                            "tools_software": "Tools and software used",
                            "datasets": "Datasets",
                            "metrics": "Metrics and evaluation criteria"
                        }
                    }
                }
            }
        
        # تحويل إلى نص prompt
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
TEXT TO ANALYZE:
==========================================
{text[:8000]}

==========================================
IMPORTANT INSTRUCTIONS:
==========================================
1. Respond ONLY in valid JSON format
2. Extract ALL information thoroughly
3. Do not skip any important details
4. Maintain scientific accuracy
5. Use the exact structure provided above

BEGIN ANALYSIS:
"""
        return prompt
    
    # ═══════════════════════════════════════════════════════════════
    # 2. Advanced Mind Map Generator (inspired by user examples)
    # ═══════════════════════════════════════════════════════════════
    
    def get_mindmap_generation_prompt(
        self,
        text: str,
        language: str = "ar",
        depth: int = 4,
        min_nodes: int = 15
    ) -> str:
        """
        Prompt متقدم لتوليد خرائط ذهنية شاملة
        
        Args:
            text: النص المراد تحليله
            language: اللغة
            depth: عمق المستويات (2-5)
            min_nodes: الحد الأدنى للعقد (10-50)
        """
        
        if language == "ar":
            prompt_structure = {
                "task": "إنشاء خريطة ذهنية شاملة ومتعددة المستويات",
                "visualization_type": "Hierarchical Mind Map",
                "language": "Arabic",
                "reading_direction": "Right to Left",
                "requirements": {
                    "minimum_nodes": min_nodes,
                    "depth_levels": depth,
                    "minimum_relationships": min_nodes // 2
                },
                "instructions": {
                    "step_1_central_topic": {
                        "description": "حدد الموضوع المركزي الرئيسي بدقة",
                        "requirements": [
                            "يجب أن يكون واضحاً ومختصراً (3-8 كلمات)",
                            "يعبر عن جوهر المحتوى",
                            "مكتوب بلغة واضحة وسليمة"
                        ]
                    },
                    "step_2_main_branches": {
                        "description": "استخرج الفروع الرئيسية",
                        "count": "6-10 فروع",
                        "categories": [
                            "الأفكار الرئيسية",
                            "المفاهيم الأساسية",
                            "المحاور الكبرى",
                            "الأقسام الهامة"
                        ],
                        "for_each_branch": {
                            "id": "معرّف فريد (uuid or number)",
                            "name": "اسم الفرع (واضح ومختصر)",
                            "category": "التصنيف (مفهوم/عملية/نتيجة/منهج/...)",
                            "importance_score": "float (0.0-1.0)",
                            "color_code": "لون مقترح (#hex)",
                            "icon_suggestion": "أيقونة مقترحة (emoji or name)",
                            "description": "وصف موجز (جملة واحدة)",
                            "keywords": ["كلمة1", "كلمة2", "..."]
                        }
                    },
                    "step_3_sub_branches": {
                        "description": f"أنشئ {depth} مستويات من الفروع الفرعية",
                        "rules": [
                            "كل فرع رئيسي يحتوي على 3-5 فروع فرعية",
                            "الفروع الفرعية تحتوي على فروع أعمق حتى المستوى {depth}",
                            "كلما زاد العمق، قل عدد الفروع (هرمي)",
                            "يجب أن تكون جميع الفروع مترابطة منطقياً"
                        ],
                        "for_each_sub_branch": {
                            "id": "معرّف فريد",
                            "name": "اسم الفرع الفرعي",
                            "parent_id": "معرّف الفرع الأب",
                            "level": "المستوى (1-{depth})",
                            "details": "تفاصيل إضافية",
                            "examples": ["مثال1", "مثال2"],
                            "importance_score": "float (0.0-1.0)"
                        }
                    },
                    "step_4_relationships": {
                        "description": "حدد العلاقات بين المفاهيم المختلفة",
                        "relationship_types": [
                            "يؤدي_إلى",
                            "يعتمد_على",
                            "يتناقض_مع",
                            "يدعم",
                            "جزء_من",
                            "مشابه_لـ",
                            "سبب_ونتيجة",
                            "يكمل"
                        ],
                        "minimum_count": min_nodes // 2,
                        "for_each_relationship": {
                            "source_id": "معرّف العقدة المصدر",
                            "target_id": "معرّف العقدة الهدف",
                            "relationship_type": "نوع العلاقة (من الأنواع أعلاه)",
                            "strength": "float (0.0-1.0)",
                            "description": "وصف العلاقة",
                            "bidirectional": "boolean (هل العلاقة ثنائية الاتجاه؟)"
                        }
                    },
                    "step_5_metadata": {
                        "description": "معلومات إضافية للخريطة",
                        "extract": {
                            "keywords": "20-30 كلمة مفتاحية من المحتوى",
                            "named_entities": {
                                "persons": ["الأشخاص المذكورين"],
                                "organizations": ["المنظمات"],
                                "locations": ["الأماكن"],
                                "technologies": ["التقنيات"],
                                "concepts": ["المفاهيم العلمية"]
                            },
                            "statistics": [
                                {
                                    "label": "وصف الإحصائية",
                                    "value": "القيمة",
                                    "unit": "الوحدة"
                                }
                            ],
                            "summary": "ملخص الخريطة في 2-3 جمل"
                        }
                    }
                },
                "output_format": {
                    "format": "JSON",
                    "structure": {
                        "central_topic": {
                            "id": "str",
                            "text": "str",
                            "subtitle": "str (optional)"
                        },
                        "main_branches": ["array of branch objects"],
                        "sub_branches": ["array of sub-branch objects"],
                        "relationships": ["array of relationship objects"],
                        "metadata": "object",
                        "visualization_hints": {
                            "suggested_layout": "hierarchical/radial/force-directed",
                            "color_scheme": "متناسق/تباين/أحادي",
                            "node_sizes": "ديناميكي حسب الأهمية",
                            "edge_styles": "حسب نوع العلاقة"
                        }
                    }
                },
                "quality_requirements": [
                    f"يجب أن تحتوي الخريطة على {min_nodes}+ عقدة على الأقل",
                    f"يجب أن يكون هناك {depth} مستويات على الأقل",
                    "جميع العقد يجب أن تكون مترابطة منطقياً",
                    "لا توجد عقد معزولة (كل عقدة لها علاقة واحدة على الأقل)",
                    "الأسماء واضحة ومختصرة",
                    "التصنيفات دقيقة ومناسبة"
                ]
            }
        else:  # English version
            prompt_structure = {
                "task": "Create comprehensive multi-level mind map",
                # Similar structure but in English
                # ... (abbreviated for brevity)
            }
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
TEXT TO ANALYZE:
==========================================
{text[:8000]}

==========================================
CRITICAL REQUIREMENTS:
==========================================
1. Create AT LEAST {min_nodes} nodes
2. Build {depth} levels of depth
3. Establish meaningful relationships between concepts
4. Use clear, concise labels
5. Ensure all nodes are connected (no isolated nodes)
6. Return ONLY valid JSON (no additional text)

BEGIN MIND MAP GENERATION:
"""
        return prompt
    
    # ═══════════════════════════════════════════════════════════════
    # 3. Arabic Poetry & Rhetoric Analysis (من أمثلة المستخدم)
    # ═══════════════════════════════════════════════════════════════
    
    def get_poetry_rhetorical_analysis_prompt(
        self,
        poetic_line: str,
        include_grammar: bool = True,
        include_rhetoric: bool = True
    ) -> str:
        """
        تحليل شامل للبيت الشعري (نحو + بلاغة)
        
        Args:
            poetic_line: البيت الشعري
            include_grammar: تضمين التحليل النحوي
            include_rhetoric: تضمين التحليل البلاغي
        """
        
        prompt_structure = {
            "prompt_type": "Arabic Poetry Comprehensive Analysis",
            "language": "Arabic",
            "reading_direction": "Right to Left",
            "input": {
                "poetic_line": poetic_line
            },
            "analysis_sections": {}
        }
        
        if include_grammar:
            prompt_structure["analysis_sections"]["grammatical_analysis"] = {
                "title": "التحليل النحوي والإعرابي",
                "word_analysis_table": {
                    "columns": [
                        "الكلمة",
                        "نوعها (اسم/فعل/حرف)",
                        "الإعراب الكامل",
                        "علامة الإعراب",
                        "المعنى اللغوي",
                        "الجذر (إن وُجد)",
                        "الوزن الصرفي"
                    ],
                    "requirements": [
                        "تحليل جميع كلمات البيت دون استثناء",
                        "الإعراب مطابق لقواعد النحو العربي الكلاسيكية",
                        "ذكر الشواهد النحوية إن أمكن"
                    ]
                },
                "overall_structure": {
                    "sentence_type": "الجملة (اسمية/فعلية)",
                    "grammatical_observations": ["ملاحظات نحوية عامة"],
                    "syntactic_complexity": "مستوى التعقيد النحوي (1-10)"
                }
            }
        
        if include_rhetoric:
            prompt_structure["analysis_sections"]["rhetorical_analysis"] = {
                "title": "التحليل البلاغي",
                "rhetoric_table": {
                    "columns": ["نوع البلاغة", "الوصف", "الموضع في البيت", "التأثير"],
                    "extract_all": [
                        {
                            "category": "علم البيان",
                            "types": [
                                "التشبيه",
                                "الاستعارة (تصريحية/مكنية)",
                                "الكناية",
                                "المجاز (مرسل/عقلي)"
                            ]
                        },
                        {
                            "category": "علم البديع",
                            "types": [
                                "الطباق",
                                "المقابلة",
                                "الجناس",
                                "السجع",
                                "التورية",
                                "حسن التقسيم"
                            ]
                        },
                        {
                            "category": "علم المعاني",
                            "types": [
                                "الخبر والإنشاء",
                                "القصر",
                                "الإيجاز والإطناب",
                                "المساواة"
                            ]
                        }
                    ]
                },
                "imagery": {
                    "visual_imagery": "الصور البصرية في البيت",
                    "auditory_imagery": "الصور السمعية",
                    "emotional_tone": "الطابع العاطفي (حزن/فرح/حماس/...)",
                    "poetic_meter": "البحر الشعري (إن أمكن تحديده)"
                }
            }
        
        # General interpretation
        prompt_structure["analysis_sections"]["general_interpretation"] = {
            "title": "الشرح العام والتفسير",
            "provide": {
                "literal_meaning": "المعنى الحرفي للبيت",
                "deeper_meaning": "المعنى الأعمق والمقصد",
                "context": "السياق التاريخي أو الأدبي (إن تعرّفت على البيت)",
                "poet_name": "اسم الشاعر (إن علمته)",
                "period": "الفترة الزمنية (جاهلي/إسلامي/عباسي/...)",
                "themes": ["الأغراض الشعرية: فخر/رثاء/غزل/حكمة/..."]
            }
        }
        
        prompt_structure["output_format"] = {
            "format": "JSON",
            "structure": {
                "poetic_line": "البيت الشعري كما أُدخل",
                "grammatical_analysis": "كائن يحتوي على التحليل النحوي" if include_grammar else None,
                "rhetorical_analysis": "كائن يحتوي على التحليل البلاغي" if include_rhetoric else None,
                "general_interpretation": "كائن التفسير العام",
                "educational_level": "المستوى التعليمي المناسب (ابتدائي/إعدادي/ثانوي/جامعي)",
                "difficulty_score": "مستوى صعوبة البيت (1-10)"
            }
        }
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
QUALITY REQUIREMENTS:
==========================================
1. الالتزام التام بقواعد النحو والصرف العربي الفصيح
2. تحليل شامل لا يتجاهل أي جانب
3. شرح بلغة عربية سهلة الفهم
4. دقة علمية عالية
5. إرجاع JSON فقط بدون نص إضافي

BEGIN ANALYSIS:
"""
        return prompt
    
    # ═══════════════════════════════════════════════════════════════
    # 4. Linguistic Analysis (Morphological + Syntactic)
    # ═══════════════════════════════════════════════════════════════
    
    def get_linguistic_deep_analysis_prompt(
        self,
        text: str,
        language: str = "ar",
        analysis_types: List[str] = None
    ) -> str:
        """
        تحليل لغوي عميق متعدد الأبعاد
        
        Args:
            text: النص المراد تحليله
            language: اللغة
            analysis_types: أنواع التحليل ["morphology", "syntax", "semantics", "discourse"]
        """
        
        if analysis_types is None:
            analysis_types = ["morphology", "syntax", "semantics", "terminology"]
        
        if language == "ar":
            prompt_structure = {
                "task": "تحليل لغوي عربي متعدد المستويات",
                "language": "Arabic",
                "text_sample": text[:2000],
                "analysis_dimensions": {}
            }
            
            if "morphology" in analysis_types:
                prompt_structure["analysis_dimensions"]["morphological_analysis"] = {
                    "description": "تحليل صرفي شامل",
                    "extract": {
                        "roots_and_patterns": [
                            {
                                "word": "الكلمة",
                                "root": "الجذر الثلاثي أو الرباعي",
                                "pattern": "الوزن الصرفي",
                                "type": "مجرد/مزيد",
                                "derivation": "المشتقات"
                            }
                        ],
                        "top_roots": "أكثر 20 جذر تكراراً",
                        "morphological_phenomena": [
                            "الإعلال",
                            "الإبدال",
                            "الإدغام",
                            "الحذف"
                        ],
                        "statistics": {
                            "trilateral_roots": "عدد الجذور الثلاثية",
                            "quadrilateral_roots": "عدد الجذور الرباعية",
                            "augmented_forms": "عدد الصيغ المزيدة"
                        }
                    }
                }
            
            if "syntax" in analysis_types:
                prompt_structure["analysis_dimensions"]["syntactic_analysis"] = {
                    "description": "تحليل نحوي",
                    "extract": {
                        "pos_distribution": {
                            "nouns": "نسبة الأسماء",
                            "verbs": "نسبة الأفعال",
                            "particles": "نسبة الحروف"
                        },
                        "sentence_structures": [
                            "الجمل الاسمية",
                            "الجمل الفعلية",
                            "الجمل المركبة"
                        ],
                        "grammatical_patterns": "الأنماط النحوية الشائعة",
                        "complexity_score": "درجة التعقيد النحوي (1-10)"
                    }
                }
            
            if "semantics" in analysis_types:
                prompt_structure["analysis_dimensions"]["semantic_analysis"] = {
                    "description": "تحليل دلالي",
                    "extract": {
                        "semantic_fields": "المجالات الدلالية المهيمنة",
                        "polysemy": "الكلمات متعددة المعاني",
                        "synonyms_groups": "مجموعات المترادفات",
                        "antonyms_pairs": "أزواج الأضداد",
                        "collocations": "التراكيب اللغوية الشائعة"
                    }
                }
            
            if "terminology" in analysis_types:
                prompt_structure["analysis_dimensions"]["terminology_extraction"] = {
                    "description": "استخراج المصطلحات",
                    "extract": {
                        "single_word_terms": "مصطلحات من كلمة واحدة",
                        "compound_terms": [
                            {
                                "term": "المصطلح المركب",
                                "frequency": "عدد مرات الظهور",
                                "definition": "التعريف (إن أمكن استنتاجه)",
                                "context": "السياق"
                            }
                        ],
                        "technical_vocabulary": "المفردات التقنية المتخصصة",
                        "glossary": "قاموس مصطلحات (عربي-إنجليزي إن أمكن)"
                    }
                }
        
        else:  # English or other languages
            prompt_structure = {
                "task": "Multi-level Linguistic Analysis",
                "language": language.upper(),
                # Similar structure...
            }
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
TEXT TO ANALYZE:
==========================================
{text[:5000]}

==========================================
INSTRUCTIONS:
==========================================
1. Perform thorough analysis on all specified dimensions
2. Extract specific examples for each category
3. Provide statistical summaries
4. Return only valid JSON
5. Be as comprehensive as possible

BEGIN LINGUISTIC ANALYSIS:
"""
        return prompt
    
    # ═══════════════════════════════════════════════════════════════
    # 5. Comparative Study Prompt
    # ═══════════════════════════════════════════════════════════════
    
    def get_comparative_analysis_prompt(
        self,
        texts: List[Dict[str, str]],
        comparison_aspects: List[str] = None
    ) -> str:
        """
        تحليل مقارن بين نصوص متعددة
        
        Args:
            texts: قائمة من النصوص [{"title": "...", "content": "..."}]
            comparison_aspects: جوانب المقارنة
        """
        
        if comparison_aspects is None:
            comparison_aspects = [
                "methodology",
                "results",
                "conclusions",
                "strengths_weaknesses",
                "innovation"
            ]
        
        prompt_structure = {
            "task": "تحليل مقارن متعدد الأبعاد",
            "number_of_texts": len(texts),
            "texts_metadata": [
                {"id": i+1, "title": t["title"]} for i, t in enumerate(texts)
            ],
            "comparison_dimensions": {
                "similarities": {
                    "description": "أوجه التشابه بين النصوص",
                    "categories": [
                        "المواضيع المشتركة",
                        "المناهج المستخدمة",
                        "النتائج المتقاربة",
                        "المراجع المشتركة"
                    ]
                },
                "differences": {
                    "description": "أوجه الاختلاف",
                    "categories": [
                        "اختلاف المنهجية",
                        "اختلاف النتائج",
                        "اختلاف التوصيات",
                        "اختلاف وجهات النظر"
                    ]
                },
                "complementarity": {
                    "description": "كيف تكمل النصوص بعضها؟",
                    "aspects": [
                        "الفجوات التي يسدها كل نص",
                        "الإضافة الفريدة لكل نص",
                        "التكامل المحتمل"
                    ]
                },
                "contradictions": {
                    "description": "التناقضات أو الاختلافات الجوهرية",
                    "extract": [
                        {
                            "aspect": "الجانب المتناقض",
                            "text_1_position": "موقف النص الأول",
                            "text_2_position": "موقف النص الثاني",
                            "resolution": "محاولة للتوفيق أو التفسير"
                        }
                    ]
                },
                "quality_ranking": {
                    "description": "ترتيب النصوص حسب الجودة والإسهام",
                    "criteria": [
                                "الجدة والابتكار",
                        "قوة المنهجية",
                        "عمق التحليل",
                        "وضوح العرض",
                        "الاستدلال العلمي"
                    ],
                    "ranking": [
                        {
                            "rank": "int",
                            "text_id": "int",
                            "overall_score": "float (0-10)",
                            "justification": "str"
                        }
                    ]
                },
                "synthesis": {
                    "description": "تركيب معرفي من جميع النصوص",
                    "provide": {
                        "unified_perspective": "رؤية موحدة من جميع النصوص",
                        "integrated_findings": "النتائج المتكاملة",
                        "future_research_directions": "اتجاهات بحثية مستقبلية مقترحة",
                        "practical_implications": "التطبيقات العملية المشتركة"
                    }
                }
            },
            "output_format": {
                "format": "JSON",
                "structure": {
                    "executive_summary": "ملخص تنفيذي للمقارنة",
                    "detailed_comparison": "مقارنة تفصيلية",
                    "visual_suggestions": "اقتراحات للتصور البصري (جداول/رسوم)",
                    "references_network": "شبكة المراجع المتقاطعة"
                }
            }
        }
        
        # إضافة النصوص
        texts_section = "\n\n".join([
            f"""
TEXT {i+1}: {t['title']}
{'='*80}
{t['content'][:3000]}
"""
            for i, t in enumerate(texts)
        ])
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
TEXTS TO COMPARE:
==========================================
{texts_section}

==========================================
REQUIREMENTS:
==========================================
1. Compare ALL texts thoroughly
2. Identify both similarities and differences
3. Provide objective quality assessment
4. Synthesize insights from all sources
5. Return only valid JSON

BEGIN COMPARATIVE ANALYSIS:
"""
        return prompt
    
    # ═══════════════════════════════════════════════════════════════
    # 6. Utility Methods
    # ═══════════════════════════════════════════════════════════════
    
    def get_prompt(
        self,
        analysis_type: AnalysisType,
        **kwargs
    ) -> str:
        """
        الحصول على Prompt حسب النوع
        
        Args:
            analysis_type: نوع التحليل
            **kwargs: معاملات إضافية
        """
        
        if analysis_type == AnalysisType.RESEARCH_PAPER:
            return self.get_research_paper_deep_analysis_prompt(**kwargs)
        elif analysis_type == AnalysisType.MINDMAP:
            return self.get_mindmap_generation_prompt(**kwargs)
        elif analysis_type == AnalysisType.POETRY_ANALYSIS:
            return self.get_poetry_rhetorical_analysis_prompt(**kwargs)
        elif analysis_type == AnalysisType.LINGUISTIC_ANALYSIS:
            return self.get_linguistic_deep_analysis_prompt(**kwargs)
        elif analysis_type == AnalysisType.COMPARATIVE_STUDY:
            return self.get_comparative_analysis_prompt(**kwargs)
        elif analysis_type == AnalysisType.ANATOMICAL_VIEW:
            return self.get_anatomical_exploded_view_prompt(**kwargs)
        elif analysis_type == AnalysisType.VISUAL_INFOGRAPHIC:
            return self.get_poetry_infographic_prompt(**kwargs)
        elif analysis_type == AnalysisType.DATA_VISUALIZATION:
            return self.get_data_visualization_prompt(**kwargs)
        elif analysis_type == AnalysisType.MATHEMATICAL_DIAGRAM:
            return self.get_mathematical_diagram_prompt(**kwargs)
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")
    
    # ═══════════════════════════════════════════════════════════════
    # 6. Visual Content Generation Prompts
    # ═══════════════════════════════════════════════════════════════
    
    def get_anatomical_exploded_view_prompt(
        self,
        organism_name: str,
        language: str = "ar"
    ) -> str:
        """
        Prompt لتوليد رسم تشريحي متفجر (exploded view)
        
        Args:
            organism_name: اسم الكائن الحي
            language: اللغة
        """
        
        prompt_structure = {
            "variables": {
                "ORGANISM_NAME": organism_name
            },
            "promptDetails": {
                "description": f"Ultra-detailed anatomical exploded view (exploded-view) and layered biological infographic of {organism_name}, presented as an educational, clinical-clear scientific visual.\n\nSpecies-accuracy rule (mandatory): Automatically infer the correct anatomy for {organism_name}. If it is a vertebrate, show an internal skeleton (skull, spine, ribs, limb bones as applicable). If it is an invertebrate, show the appropriate exoskeleton/segments and primary support structures. Automatically choose the correct respiratory organs for {organism_name} (lungs, gills, tracheal system, etc.). Depict the reproductive system in a measured, educational manner (no explicit nudity).\n\nCamera and composition:\n- 3/4 front isometric angle, scientific product/anatomy render perspective.\n- Main body centered; outer body partially transparent and opened.\n- Anatomical layers and major systems are separated and floating around the main body in a clean, symmetric, hierarchical exploded layout.\n- Even spacing between layers; no clutter.\n- Callout leader lines never cross; labels stay inside the frame and remain highly legible.\n\nLayers and systems (outer to inner, species-appropriate):\n1) Outer surface: skin or exoskeleton/outer tissue.\n2) Support system: skeleton or exoskeleton/segments.\n3) Muscular system: major muscle groups and tendon attachments.\n4) Circulatory system: heart and major vessels (avoid messy capillary over-detail).\n5) Respiratory system: species-appropriate organs.\n6) Digestive system: stomach/gizzard (if applicable), intestines, liver and associated organs.\n7) Nervous system: brain or ganglia structures, primary nerve pathways.\n8) Reproductive system: species-appropriate core structures.\n9) Signature anatomy: highlight {organism_name}-specific distinctive structures (wings, fins, tail, horns, pouches, antennae, etc.) as separate emphasized layers.\n\nLabeling (mandatory):\n- Thin white leader lines + numbered labels.\n- Typeface: minimalist sans-serif, high legibility.\n- Label format: \"## Part Name (System)\". Example: \"03 Sternum (Skeletal)\".\n- Use 12–24 labels total; no duplicate numbers.\n\nVisual style and quality:\n- Photorealistic 3D medical/anatomy render + textbook infographic aesthetic.\n- Clinical clarity, high contrast, razor-sharp detail, 8K.\n- Clean composition, strong negative space management, educational focus.\n\nLighting and background:\n- Soft, even studio lighting; controlled reflections.\n- Background: seamless smooth dark gray or dark navy scientific studio backdrop.",
                "styleTags": [
                    "Anatomical Exploded View",
                    "Medical/Biological Infographic",
                    "Layered Anatomy",
                    "Photorealistic 3D Anatomy Render",
                    "Educational Scientific Style",
                    "Minimalist Labels",
                    "Dark Studio Background",
                    "Clinical clarity",
                    "Exploded view hierarchy"
                ]
            },
            "negativePrompt": "blood, gore, horror, surgery scene, open wounds, excessive graphic content, real-person portrait, human-identity face, celebrity likeness, messy exploded layout, unnecessary extra organs/limbs, incorrect anatomy, blurry labels, unreadable text, crossed/overlapping leader lines, cartoon style, low-poly, watermark, logo, broken perspective, excessive noise, heavy motion blur",
            "generationTips": {
                "aspectRatio": "2:3",
                "detailLevel": "ultra",
                "stylization": "low-medium",
                "camera": {
                    "angle": "3/4 front isometric",
                    "lens": "scientific product/anatomy render perspective"
                },
                "lighting": "soft, even, medical-illustration clarity",
                "background": "seamless smooth dark gray or dark navy",
                "compositionLocks": [
                    "no crossing leader lines",
                    "labels legible and inside frame",
                    "even spacing and clear hierarchy between layers"
                ]
            }
        }
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
GENERATION INSTRUCTIONS:
==========================================
1. Create ultra-detailed anatomical exploded view
2. Ensure species-accurate anatomy
3. Use clean, hierarchical layout
4. Add clear numbered labels (12-24)
5. Maintain clinical clarity and educational focus
6. Follow all composition and lighting rules

GENERATE IMAGE:
"""
        return prompt
    
    def get_poetry_infographic_prompt(
        self,
        poetic_line: str,
        analysis_focus: str = "rhetoric"  # "grammar" or "rhetoric"
    ) -> str:
        """
        Prompt لتوليد infographic تعليمي للشعر العربي
        
        Args:
            poetic_line: البيت الشعري
            analysis_focus: التركيز ("grammar" للنحو، "rhetoric" للبلاغة)
        """
        
        if analysis_focus == "grammar":
            prompt_structure = {
                "prompt_type": "Educational Infographic - Arabic Grammar & Poetry",
                "language": "Arabic",
                "page_size": "A4",
                "orientation": "Vertical",
                "reading_direction": "Right to Left",
                "title": "شرح وإعراب بيت شعري",
                "input_instruction": f"البيت الشعري: {poetic_line}",
                "content_structure": {
                    "section_1": {
                        "name": "البيت الشعري",
                        "description": "عرض البيت الشعري بخط عربي جميل وواضح مع تشكيل مناسب إن أمكن"
                    },
                    "section_2": {
                        "name": "جدول شرح وإعراب الكلمات",
                        "table_columns": [
                            "الكلمة",
                            "نوعها (اسم / فعل / حرف)",
                            "شرح المعنى اللغوي",
                            "الإعراب الكامل",
                            "علامة الإعراب"
                        ],
                        "table_rules": [
                            "تحليل جميع كلمات البيت دون استثناء",
                            "الإعراب مطابق لقواعد النحو العربي الموثوقة",
                            "الشرح مبسط ومناسب للمستوى التعليمي"
                        ]
                    },
                    "section_3": {
                        "name": "الشرح العام للبيت",
                        "description": "شرح أدبي ولغوي شامل لمعنى البيت، يوضح الفكرة العامة والصورة البلاغية إن وجدت، بلغة عربية سليمة ومبسطة"
                    }
                },
                "design_style": {
                    "style": "Modern Educational Infographic",
                    "colors": "هادئة ومريحة للعين",
                    "icons": "أيقونات تعليمية بسيطة",
                    "fonts": "خط عربي واضح وأنيق (مثل Tajawal, Cairo, Amiri)",
                    "layout": "منظم، متوازن، سهل القراءة"
                },
                "accuracy_requirements": [
                    "الالتزام التام بقواعد النحو والصرف",
                    "عدم حذف أو إضافة أي كلمة من البيت الشعري",
                    "تجنب الأخطاء الإعرابية أو اللغوية"
                ],
                "signature": {
                    "text": "محرك البحث الأكاديمي",
                    "placement": "أسفل الصفحة",
                    "style": "توقيع أنيق داخل إطار علمي"
                },
                "output": "صورة إنفوجرافيك تعليمية واحدة عالية الدقة جاهزة للطباعة"
            }
        else:  # rhetoric
            prompt_structure = {
                "prompt_type": "Infographic",
                "language": "Arabic",
                "input_variables": {
                    "poetic_line": poetic_line
                },
                "output": {
                    "image_style": "انفوجرافيك تعليمي جذاب بالكامل باللغة العربية",
                    "layout": "عمودي",
                    "content": {
                        "title": "البلاغة في البيت الشعري",
                        "poetic_line_display": poetic_line,
                        "table": {
                            "columns": ["نوع البلاغة", "الوصف", "مثال من البيت"],
                            "rows": "استخرج جميع أنواع البلاغة الموجودة في البيت مثل الاستعارة، الكناية، التشبيه، المحسنات البديعية، الطباق، والجناس مع شرح مبسط لكل نوع وذكر مثال مباشر من البيت"
                        },
                        "icons": "أيقونات ورسوم صغيرة تمثل كل نوع بلاغة بشكل بصري جذاب"
                    },
                    "colors": "ألوان متناسقة وجذابة تناسب التعليم والقراءة",
                    "typography": "خط عربي واضح وجميل (مثل Amiri, Tajawal, El Messiri)",
                    "signature": "محرك البحث الأكاديمي",
                    "notes": "احرص على أن يبقى التصميم عربي بالكامل، مع وضوح الجدول وتناسق العناصر بصريًا"
                }
            }
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
GENERATION INSTRUCTIONS:
==========================================
1. Create educational Arabic poetry infographic
2. Analyze ALL words in the poetic line
3. Use clear, attractive design
4. Ensure readability and educational value
5. Use appropriate Arabic fonts and RTL layout
6. Generate high-quality image suitable for printing

GENERATE INFOGRAPHIC:
"""
        return prompt
    
    def get_data_visualization_prompt(
        self,
        data_description: str,
        chart_type: str = "auto",  # "bar", "line", "pie", "scatter", "heatmap", "auto"
        language: str = "ar"
    ) -> str:
        """
        Prompt ذكي لتوليد تصور بيانات احترافي
        
        Args:
            data_description: وصف البيانات أو البيانات الفعلية
            chart_type: نوع الرسم البياني
            language: اللغة
        """
        
        prompt_structure = {
            "task": "إنشاء تصور بيانات احترافي" if language == "ar" else "Create professional data visualization",
            "language": language,
            "data_input": data_description,
            "visualization_specs": {
                "chart_type": chart_type,
                "auto_selection": "إذا كان النوع 'auto'، اختر النوع الأنسب للبيانات" if language == "ar" else "If type is 'auto', choose the most appropriate chart type",
                "style_requirements": [
                    "Clean, professional design",
                    "High contrast for readability",
                    "Appropriate color palette",
                    "Clear axis labels and legends",
                    "Data labels where helpful",
                    "Minimalist, modern aesthetic"
                ],
                "elements_to_include": [
                    "Title (descriptive and clear)",
                    "Axis labels (with units if applicable)",
                    "Legend (if multiple series)",
                    "Data source annotation",
                    "Grid lines (subtle)",
                    "Statistical summaries if relevant (mean, median, etc.)"
                ]
            },
            "design_guidelines": {
                "colors": "Use a professional color scheme (avoid overly bright or clashing colors)",
                "typography": "Clear, sans-serif fonts for labels",
                "spacing": "Adequate white space, not cluttered",
                "annotations": "Highlight key insights or outliers",
                "accessibility": "Ensure color-blind friendly palette"
            },
            "output_format": {
                "format": "High-resolution image (PNG or SVG)",
                "dimensions": "Appropriate for presentation or publication",
                "quality": "Print-ready quality (300 DPI minimum)"
            }
        }
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
VISUALIZATION REQUIREMENTS:
==========================================
1. Analyze the data and choose the most effective visualization
2. Use professional design principles
3. Ensure clarity and readability
4. Highlight key insights
5. Make it publication-ready
6. Follow accessibility guidelines

GENERATE VISUALIZATION:
"""
        return prompt
    
    def get_mathematical_diagram_prompt(
        self,
        concept: str,
        diagram_type: str = "geometric",  # "geometric", "algebraic", "calculus", "statistics"
        language: str = "ar"
    ) -> str:
        """
        Prompt لتوليد رسوم توضيحية رياضية
        
        Args:
            concept: المفهوم الرياضي
            diagram_type: نوع الرسم
            language: اللغة
        """
        
        prompt_structure = {
            "task": f"إنشاء رسم توضيحي رياضي لـ: {concept}" if language == "ar" else f"Create mathematical diagram for: {concept}",
            "language": language,
            "concept": concept,
            "diagram_type": diagram_type,
            "specifications": {
                "style": "Educational mathematical illustration",
                "clarity": "Maximum clarity for student understanding",
                "accuracy": "Mathematically precise and accurate",
                "annotations": [
                    "Clear labels for all components",
                    "Mathematical notation where appropriate",
                    "Step-by-step visual breakdown if applicable",
                    "Color-coded elements for better understanding"
                ],
                "visual_elements": [
                    "Coordinate axes (if applicable)",
                    "Grid or background structure",
                    "Arrows and direction indicators",
                    "Highlighted key areas",
                    "Measurements and dimensions"
                ]
            },
            "educational_features": [
                "Show visual proof or demonstration",
                "Include formula or equation representation",
                "Use analogies or real-world connections",
                "Provide visual intuition"
            ],
            "design_aesthetics": {
                "colors": "Professional, educational color scheme",
                "fonts": "Clear mathematical fonts (LaTeX-style for equations)",
                "layout": "Balanced and uncluttered",
                "background": "Clean, light background for textbook style"
            }
        }
        
        prompt = f"""
{json.dumps(prompt_structure, ensure_ascii=False, indent=2)}

==========================================
DIAGRAM REQUIREMENTS:
==========================================
1. Create mathematically accurate visualization
2. Use clear educational style
3. Include proper mathematical notation
4. Make it intuitive and understandable
5. Add helpful annotations and labels
6. Suitable for textbooks or educational materials

GENERATE MATHEMATICAL DIAGRAM:
"""
        return prompt
    
    def detect_language(self, text: str) -> str:
        """كشف لغة النص تلقائياً"""
        # كشف بسيط بناءً على الأحرف
        arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            return "unknown"
        
        arabic_ratio = arabic_chars / total_chars
        
        if arabic_ratio > 0.3:
            return "ar"
        else:
            return "en"


# ═══════════════════════════════════════════════════════════════
# Example Usage
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # إنشاء مكتبة
    library = IntelligentPromptsLibrary(language="ar")
    
    # Example 1: Research Paper Analysis
    research_text = """
    العنوان: تأثير الذكاء الاصطناعي على التعليم العالي
    الملخص: يهدف هذا البحث إلى دراسة تأثير تقنيات الذكاء الاصطناعي...
    """
    
    prompt1 = library.get_prompt(
        AnalysisType.RESEARCH_PAPER,
        text=research_text,
        language="ar",
        analysis_depth="deep"
    )
    
    print("="*80)
    print("RESEARCH PAPER ANALYSIS PROMPT")
    print("="*80)
    print(prompt1[:500], "...")
    
    # Example 2: Mind Map Generation
    prompt2 = library.get_prompt(
        AnalysisType.MINDMAP,
        text=research_text,
        language="ar",
        depth=4,
        min_nodes=20
    )
    
    print("\n" + "="*80)
    print("MIND MAP GENERATION PROMPT")
    print("="*80)
    print(prompt2[:500], "...")
    
    # Example 3: Poetry Analysis
    poetic_line = "وإذا المنية أنشبت أظفارها * ألفيت كل تميمة لا تنفع"
    
    prompt3 = library.get_prompt(
        AnalysisType.POETRY_ANALYSIS,
        poetic_line=poetic_line,
        include_grammar=True,
        include_rhetoric=True
    )
    
    print("\n" + "="*80)
    print("POETRY ANALYSIS PROMPT")
    print("="*80)
    print(prompt3[:500], "...")
