from anyio import Path
from sentence_transformers import SentenceTransformer, util
import os
import numpy as np
from typing import List, Optional, Tuple


from ocr import extract_chunks


model = SentenceTransformer('all-MiniLM-L6-v2')
model = model.to('cpu')

class Document:
    def __init__(self, path: str, embeddings: Optional[List[np.ndarray]]=None):
        self.path = path

        if embeddings is not None:
            self.embeddings = embeddings
            return

        # compute embedding
        self.embeddings = compute_document_embeddings(path)

    def __str__(self):
        return self.path

    def __repr__(self):
        return self.__str__()

    def serialize(self) -> dict:
        return {
            'path': self.path,
            'embeddings': np.array(self.embeddings)
        }

    @staticmethod
    def deserialize(data: dict) -> 'Document':
        path = data['path']
        embeddings = [np.array(emb) for emb in data['embeddings']]
        return Document(path, embeddings=embeddings)

def compute_text_embedding(text: str) -> np.ndarray:
    embedding = model.encode(text, convert_to_tensor=True)
    return embedding

def compute_document_embeddings(path: str) -> List[np.ndarray]:
    """
    returns a list of embeddings for the sentences in the document
    """
    chunks = extract_chunks(path)
    embeddings = [model.encode(chunk, convert_to_tensor=True) for chunk in chunks]
    return embeddings

def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

def search_documents(query: str, documents: List[Document], top_k: int=5) -> List[Document]:
    query_embedding = compute_text_embedding(query)
    similarities = []

    for idx, doc in enumerate(documents):
        if len(doc.embeddings) == 0:
            continue
        # Save maximum similarity across all embeddings in the document
        doc_similarities = [compute_similarity(query_embedding, emb) for emb in doc.embeddings]
        similarities.append((max(doc_similarities), idx))

    # Sort documents by similarity score in descending order
    similarities.sort(key=lambda x: x[0], reverse=True)

    # Return top_k documents
    top_documents = [documents[idx] for _, idx in similarities[:top_k]]
    return top_documents

def extract_file_paths(dir_path: str, types: Tuple[str]) -> List[str]:
    file_paths = []
    for filename in os.listdir(dir_path):

        if filename == '.recollect':
            continue

        if '.' in filename and filename.split('.')[-1].lower() in types and not os.path.isdir(os.path.join(dir_path, filename)):
            file_paths.append(os.path.join(dir_path, filename))

        elif os.path.isdir(os.path.join(dir_path, filename)):
            sub_dir_paths = extract_file_paths(os.path.join(dir_path, filename), types)
            file_paths.extend(sub_dir_paths)

    return file_paths

def save_index(index_path: str, documents: List[Document]):

    os.makedirs(index_path, exist_ok=True)

    index_data = {"documents": []}
    for i, doc in enumerate(documents):
        emb_path = f"doc_{i}_embeddings.npz"
        np.savez(os.path.join(index_path, emb_path), *doc.embeddings)
        index_data["documents"].append({
            "path": doc.path,
            "embeddings_file": emb_path
        })

    with open(os.path.join(index_path, "index.json"), "w") as f:
        import json
        json.dump(index_data, f)

def load_index(index_path: str) -> List[Document]:
    import json
    with open(Path(index_path) / "index.json", "r") as f:
        index_data = json.load(f)

    documents = []
    for doc_data in index_data["documents"]:
        emb_file = Path(index_path) / doc_data["embeddings_file"]
        loaded = np.load(emb_file)
        embeddings = [loaded[key] for key in loaded]
        document = Document(doc_data["path"], embeddings=embeddings)
        documents.append(document)

    return documents

def create_index(dir_path: str, allow_types: Optional[Tuple[str]] = ('pdf', 'png', 'jpg', 'txt'), use_cache=True) -> List[Document]:
    """
    Create an index of documents from the specified directory.
    """

    # check if cached index exists
    if use_cache and os.path.exists(os.path.join(dir_path, '.recollect')):
        documents = load_index(os.path.join(dir_path, '.recollect'))

        # only return if we actually loaded an index
        if len(documents) > 0:
            return documents

    documents = []
    for filepath in extract_file_paths(dir_path, allow_types):
        document = Document(filepath)
        documents.append(document)

    # save cached index
    if use_cache:
        save_index(os.path.join(dir_path, '.recollect'), documents)

    return documents

def run_tests():
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "data")
    filepaths = extract_file_paths(test_data_dir, ('txt',))
    filenames = [os.path.basename(fp) for fp in filepaths]
    for filename in ["construction_project.txt", "dog.txt", "horse.txt", "programmer.txt"]:
        assert filename in filenames, f"{filename} not found in extracted file paths"

    documents = create_index(test_data_dir, allow_types=('txt',))

    query = "A person who writes code"
    results = search_documents(query, documents, top_k=1)
    assert len(results) == 1
    assert results[0].path.endswith("programmer.txt")

    query = "animal"
    results = search_documents(query, documents, top_k=2)
    assert len(results) == 2
    assert results[0].path.endswith("dog.txt") or results[0].path.endswith("horse.txt")
    assert results[1].path.endswith("dog.txt") or results[1].path.endswith("horse.txt")

if __name__ == "__main__":
    run_tests()

