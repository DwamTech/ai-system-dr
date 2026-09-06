from langchain_core.documents import Document

import processor_optimized


def test_digital_pdf_recovers_sparse_scanned_page_without_renumbering(monkeypatch):
    class Loader:
        def __init__(self, _path):
            pass

        def load(self):
            return [Document(page_content="نص واضح وطويل بما يكفي في الصفحة الأولى"), Document(page_content="")]

    class Image:
        def close(self):
            pass

    monkeypatch.setattr(processor_optimized, "PyPDFLoader", Loader)
    monkeypatch.setattr(processor_optimized, "convert_from_path", lambda *args, **kwargs: [Image()])
    processor = processor_optimized.OptimizedDocumentProcessor(reporter=lambda *_: None)
    monkeypatch.setattr(processor, "_ocr_single_image_optimized", lambda _image: "Recovered English page")
    documents = processor._process_digital_pdf("fixture.pdf", "fixture.pdf")
    assert [document.metadata["page_number"] for document in documents] == [1, 2]
    assert documents[1].page_content == "Recovered English page"
    assert documents[1].metadata["processing_method"] == "ocr"
