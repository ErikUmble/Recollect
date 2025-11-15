from sentence_transformers import SentenceTransformer, util
import os
import numpy as np
from typing import List, Optional, Tuple


from .ocr import extract_sentences

model = SentenceTransformer('all-MiniLM-L6-v2')

class Document:
    def __init__(self, path: str, embeddings: Optional[List[np.ndarray]]=None):
        self.path = path

        if embeddings is not None:
            self.embeddings = embeddings
            return
        
        # compute embedding
        self.embeddings = compute_document_embeddings(path)

def compute_text_embedding(text: str) -> np.ndarray:
    embedding = model.encode(text, convert_to_tensor=True)
    return embedding

def compute_document_embeddings(path: str) -> List[np.ndarray]:
    """
    returns a list of embeddings for the sentences in the document
    """
    sentences = extract_sentences(path)
    embeddings = [model.encode(sentence, convert_to_tensor=True) for sentence in sentences]
    return embeddings

def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

def search_documents(query: str, documents: List[Document], top_k: int=5) -> List[Document]:
    query_embedding = compute_text_embedding(query)
    similarities = []

    for idx, doc in enumerate(documents):
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
        if '.' in filename and filename.split('.')[-1].lower() in types and not os.path.isdir(os.path.join(dir_path, filename)):
            file_paths.append(os.path.join(dir_path, filename))

        elif os.path.isdir(os.path.join(dir_path, filename)):
            sub_dir_paths = extract_file_paths(os.path.join(dir_path, filename), types)
            file_paths.extend(sub_dir_paths)
    
    return file_paths

def create_index(dir_path: str, allow_types: Optional[Tuple[str]] = ('pdf', 'png', 'jpg', 'txt')) -> List[Document]:
    """
    Create an index of documents from the specified directory.
    """

    documents = []
    for filepath in extract_file_paths(dir_path, allow_types):
        document = Document(filepath)
        documents.append(document)
    
    return documents