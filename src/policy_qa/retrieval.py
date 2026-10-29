"""Local Chroma retrieval using CPU MiniLM ONNX embeddings."""

import hashlib
import re
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from .schemas import Evidence

ROOT = Path(__file__).resolve().parents[2]


class PolicyIndex:
    """Index policy sections in Chroma and retrieve relevant evidence."""

    def __init__(self, root=ROOT):
        """Load policy sections, prepare their vector index, and check token limits."""
        self.root = Path(root)
        self.documents = {}
        content = b""
        for path in sorted((self.root / "data/policies").glob("*.txt")):
            raw = path.read_text(encoding="utf-8")
            content += path.name.encode() + raw.encode()
            for section in re.split(r"(?m)^## ", raw)[1:]:
                heading, body = section.split("\n", 1)
                section_id, title = heading.split(" | ", 1)
                chunk_id = f"{path.stem}/{section_id}"
                self.documents[chunk_id] = Evidence(
                    chunk_id=chunk_id,
                    document_id=path.stem,
                    section_id=section_id,
                    text=title + "\n" + body.strip(),
                )
        if not self.documents:
            raise ValueError("No policy sections found. Run scripts/generate_data.py")
        self.corpus_hash = hashlib.sha256(content).hexdigest()
        # Keep downloaded models and index inside the project, not a global cache.
        ONNXMiniLM_L6_V2.DOWNLOAD_PATH = self.root / ".runtime/embeddings"
        embedding = ONNXMiniLM_L6_V2(preferred_providers=["CPUExecutionProvider"])
        client = chromadb.PersistentClient(
            path=str(self.root / ".runtime/chroma"),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = client.get_or_create_collection(
            "policies-" + self.corpus_hash[:16],
            embedding_function=embedding,
            metadata={"hnsw:space": "cosine"},
        )
        if self.collection.count() != len(self.documents):
            docs = list(self.documents.values())
            self.collection.upsert(
                ids=[d.chunk_id for d in docs],
                documents=[d.text for d in docs],
                metadatas=[
                    {"document_id": d.document_id, "section_id": d.section_id}
                    for d in docs
                ],
            )
        # Tokenizer limits the input to 256. Validate with a non-truncating copy.
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(
            str(embedding.DOWNLOAD_PATH / "onnx/tokenizer.json")
        )
        tokenizer.no_truncation()
        for doc in self.documents.values():
            if len(tokenizer.encode(doc.text).ids) > 256:
                raise ValueError(
                    f"Section exceeds MiniLM's 256-token limit: {doc.chunk_id}"
                )

    def search(self, query: str, k=3):
        """Find the policy sections most similar to the search query."""
        result = self.collection.query(
            query_texts=[query], n_results=min(k, len(self.documents))
        )
        return [self.documents[key].model_dump() for key in result["ids"][0]]
