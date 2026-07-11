import re
import math
import uuid
from typing import List, Dict, Any, Optional

STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'arent', 'as', 'at',
    'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'cant', 'cannot', 'could',
    'couldnt', 'did', 'didnt', 'do', 'does', 'doesnt', 'doing', 'dont', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'hadnt', 'has', 'hasnt', 'have', 'havent', 'having', 'he', 'hed', 'hell', 'hes', 'her', 'here',
    'heres', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'hows', 'i', 'id', 'ill', 'im', 'ive', 'if', 'in',
    'into', 'is', 'isnt', 'it', 'its', 'itself', 'lets', 'me', 'more', 'most', 'mustnt', 'my', 'myself', 'no', 'nor',
    'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own',
    'same', 'shant', 'shed', 'shell', 'shes', 'should', 'shouldnt', 'so', 'some', 'such', 'than', 'that', 'thats',
    'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'theres', 'these', 'they', 'theyd', 'theyll',
    'theyre', 'theyve', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasnt', 'we',
    'wed', 'well', 'were', 'weve', 'werent', 'what', 'whats', 'when', 'whens', 'where', 'wheres', 'which', 'while',
    'who', 'whos', 'whom', 'why', 'whys', 'with', 'wont', 'would', 'wouldnt', 'you', 'youd', 'youll', 'youre', 'youve',
    'your', 'yours', 'yourself', 'yourselves'
}

def tokenize(text: str) -> List[str]:
    clean_text = re.sub(r'[^\w\s-]', '', text.lower())
    words = clean_text.split()
    return [w for w in words if w not in STOPWORDS and len(w) > 2]

class VectorStore:
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.chunks: List[Dict[str, Any]] = []
        self.vocab: Set[str] = set()
        self.idf: Dict[str, float] = {}

    def chunk_markdown(self, title: str, content: str, doc_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        lines = content.split('\n')
        chunks = []
        current_header = "General"
        current_lines = []
        
        chunk_idx = 0
        for line in lines:
            if line.startswith('## ') or line.startswith('### '):
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if len(chunk_text) > 40:
                        chunks.append({
                            "chunk_id": f"chunk_{title.lower().replace(' ', '_')}_{chunk_idx}",
                            "source_document": title,
                            "page_or_section": current_header,
                            "content": chunk_text,
                            "metadata": {
                                "date": doc_metadata.get("date", "2025-01-01"),
                                "author": doc_metadata.get("author", "System"),
                                "department": doc_metadata.get("department", "General"),
                                "doc_type": doc_metadata.get("doc_type", "Policy")
                            }
                        })
                        chunk_idx += 1
                current_header = line.replace('#', '').strip()
                current_lines = [line]
            else:
                current_lines.append(line)
        
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if len(chunk_text) > 40:
                chunks.append({
                    "chunk_id": f"chunk_{title.lower().replace(' ', '_')}_{chunk_idx}",
                    "source_document": title,
                    "page_or_section": current_header,
                    "content": chunk_text,
                    "metadata": {
                        "date": doc_metadata.get("date", "2025-01-01"),
                        "author": doc_metadata.get("author", "System"),
                        "department": doc_metadata.get("department", "General"),
                        "doc_type": doc_metadata.get("doc_type", "Policy")
                    }
                })
        
        return chunks

    def add_document(self, title: str, content: str, metadata: Dict[str, Any]) -> int:
        self.documents[title] = {
            "content": content,
            "metadata": metadata
        }
        
        new_chunks = self.chunk_markdown(title, content, metadata)
        self.chunks = [c for c in self.chunks if c["source_document"] != title]
        self.chunks.extend(new_chunks)
        
        self.recompute_idf()
        return len(new_chunks)

    def recompute_idf(self):
        self.vocab = set()
        doc_count = len(self.chunks)
        if doc_count == 0:
            return

        doc_frequencies = {}
        for chunk in self.chunks:
            tokens = set(tokenize(chunk["content"]))
            for token in tokens:
                self.vocab.add(token)
                doc_frequencies[token] = doc_frequencies.get(token, 0) + 1
        
        self.idf = {}
        for token, freq in doc_frequencies.items():
            self.idf[token] = math.log((doc_count + 1) / (freq + 1)) + 1.0

    def compute_tfidf_vector(self, tokens: List[str]) -> Dict[str, float]:
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        
        vector = {}
        for token, count in tf.items():
            if token in self.idf:
                vector[token] = count * self.idf[token]
        return vector

    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        intersection = set(vec1.keys()) & set(vec2.keys())
        if not intersection:
            return 0.0
        
        dot_product = sum(vec1[x] * vec2[x] for x in intersection)
        
        sum1 = sum(val**2 for val in vec1.values())
        sum2 = sum(val**2 for val in vec2.values())
        
        if sum1 == 0.0 or sum2 == 0.0:
            return 0.0
        
        return dot_product / (math.sqrt(sum1) * math.sqrt(sum2))

    def search(self, query: str, top_k: int = 5, constraints: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return [dict(c, relevance_score=0.1) for c in self.chunks[:top_k]]
            
        query_vector = self.compute_tfidf_vector(query_tokens)
        
        results = []
        for chunk in self.chunks:
            meta = chunk["metadata"]
            if constraints:
                if constraints.get("department") and meta.get("department").lower() != constraints["department"].lower():
                    continue
                if constraints.get("doc_type") and meta.get("doc_type").lower() != constraints["doc_type"].lower():
                    continue
                if constraints.get("date_range"):
                    start = constraints["date_range"].get("start")
                    end = constraints["date_range"].get("end")
                    doc_date = meta.get("date", "2020-01-01")
                    if start and doc_date < start:
                        continue
                    if end and doc_date > end:
                        continue

            chunk_tokens = tokenize(chunk["content"])
            chunk_vector = self.compute_tfidf_vector(chunk_tokens)
            
            score = self.cosine_similarity(query_vector, chunk_vector)
            overlap_count = len(set(query_tokens) & set(chunk_tokens))
            keyword_boost = 0.05 * overlap_count
            final_score = min(0.99, score + keyword_boost)
            
            if final_score > 0.0:
                results.append(dict(chunk, relevance_score=round(final_score, 3)))
                
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]

db = VectorStore()
