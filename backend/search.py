from anyio import Path
from sentence_transformers import SentenceTransformer, util
import os
import numpy as np
from typing import List, Optional, Tuple
from PIL import Image


from ocr import extract_chunks
from image_utils import extract_images_from_document
from utils import is_image_path


text_model = SentenceTransformer('all-MiniLM-L6-v2')
image_model = SentenceTransformer("clip-ViT-B-32")


class Document:
    def __init__(self, path: str, text_embeddings: Optional[List[np.ndarray]]=None, image_embeddings: Optional[List[np.ndarray]]=None):
        self.path = path

        if text_embeddings or image_embeddings is not None:
            self.text_embeddings = text_embeddings or []
            self.image_embeddings = image_embeddings or []
            return
        
        text_embeddings, image_embeddings = compute_document_embeddings(path)
        self.text_embeddings = text_embeddings
        self.image_embeddings = image_embeddings

    def __str__(self):
        return self.path
    
    def __repr__(self):
        return self.__str__()

def compute_text_embedding(text: str) -> np.ndarray:
    embedding = text_model.encode(text, convert_to_tensor=True)
    return embedding

def compute_image_embedding(img: Optional[Image.Image] = None, query: Optional[str] = None) -> np.ndarray:
    if img is not None:
        return image_model.encode(img, convert_to_tensor=True)
    if query is not None:
        return image_model.encode(query, convert_to_tensor=True)
    raise ValueError("Either img or query must be provided")

def compute_document_embeddings(path: str) -> Tuple[List[np.ndarray], List[np.ndarray]]:
    """
    returns a list of embeddings for the sentences in the document
    """
    chunks = extract_chunks(path)
    text_embeddings = [text_model.encode(chunk, convert_to_tensor=True) for chunk in chunks]
    if is_image_path(path):
        images = extract_images_from_document(path)
        image_embeddings = [compute_image_embedding(img) for img in images]
    else:
        image_embeddings = []
    return text_embeddings, image_embeddings

def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

def search_documents(query: str, documents: List[Document], top_k: int=5, image_weight: float=1.5) -> List[Document]:
    """
    return the top_k most relevant documents to the query
    image_weight: weight multiplier for image embeddings similarity (useful as images use a different embedding and similarity scale is slightly different)
    """
    query_embedding = compute_text_embedding(query)
    query_img_embedding = compute_image_embedding(query)
    similarities = []

    for idx, doc in enumerate(documents):
        if len(doc.text_embeddings) == 0 and len(doc.image_embeddings) == 0:
            continue
        # Save maximum similarity across all embeddings in the document
        doc_similarities = [compute_similarity(query_embedding, emb) for emb in doc.text_embeddings]
        doc_similarities += [image_weight * compute_similarity(query_img_embedding, emb) for emb in doc.image_embeddings]
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

def _save_index_to_cache(cache_path: str, documents: List[Document], child_cache_paths: Optional[List[str]] = None):
    os.makedirs(cache_path, exist_ok=True)

    index_data = {"documents": [], "children": child_cache_paths or []}
    for i, doc in enumerate(documents):
        text_embedding_path = f"doc_{i}_tembeddings.npz"
        img_embedding_path = f"doc_{i}_iembeddings.npz"

        if len(doc.text_embeddings) > 0:
            np.savez(os.path.join(cache_path, text_embedding_path), *doc.text_embeddings)
        
        if len(doc.image_embeddings) > 0:
            np.savez(os.path.join(cache_path, img_embedding_path), *doc.image_embeddings)

        index_data["documents"].append({
            "path": doc.path,
            "text_embeddings_file": text_embedding_path if len(doc.text_embeddings) > 0 else None,
            "image_embeddings_file": img_embedding_path if len(doc.image_embeddings) > 0 else None
        })

    with open(os.path.join(cache_path, "index.json"), "w") as f:
        import json
        json.dump(index_data, f)

    return cache_path

def _load_cached_index(cache_path: str) -> List[Document]:
    import json
    try:
        with open(os.path.join(cache_path, "index.json"), "r") as f:
            index_data = json.load(f)
        
        documents = []
        for child_cache_path in index_data["children"]:
            documents += _load_cached_index(child_cache_path)

        for doc_data in index_data["documents"]:
            text_embeddings = []
            image_embeddings = []
            if doc_data["text_embeddings_file"] is not None:
                text_emb_file = os.path.join(cache_path, doc_data["text_embeddings_file"])
                loaded = np.load(text_emb_file)
                text_embeddings = [loaded[key] for key in loaded]

            if doc_data["image_embeddings_file"] is not None:
                img_emb_file = os.path.join(cache_path, doc_data["image_embeddings_file"])
                loaded = np.load(img_emb_file)
                image_embeddings = [loaded[key] for key in loaded]

            document = Document(doc_data["path"], text_embeddings=text_embeddings, image_embeddings=image_embeddings)
            documents.append(document)

    except Exception as e:
        print(e)
        return []
    
    return documents


def _create_index_recursive(dir_path: str, allow_types: Optional[Tuple[str]], use_cache: bool, subcache_threshold: Optional[int]) -> Tuple[List[Document], List[Document], List[str]]:
    """
    returns (cached_documents, uncached_documents, children_cache_paths)
    children_cache_paths is a list of paths to child .recollect caches in subdirectories
    """
    files = []
    subdirs = []
    try:
        entries = os.listdir(dir_path)
    except PermissionError:
        return [], [], []
    
    for entry in entries:
        if os.path.isdir(os.path.join(dir_path, entry)):
            subdirs.append(entry)
        else:
            files.append(entry)

    if use_cache and ".recollect" in subdirs:
        return _load_cached_index(os.path.join(dir_path, ".recollect")), [], [os.path.join(dir_path, ".recollect")]
        
    # recursively search subdirectories
    uncached = []
    cached = []
    children_cache_paths = []
    for sub_dir in subdirs:
        if sub_dir.startswith("."):
            # skip hidden directories
            continue
        _cached, _uncached, _children_cache_paths = _create_index_recursive(os.path.join(dir_path, sub_dir), allow_types=allow_types, use_cache=use_cache, subcache_threshold=subcache_threshold)
        children_cache_paths += _children_cache_paths
        cached += _cached
        uncached += _uncached

    # now index the current directory files
    for file in files:
        if '.' in file and not file.startswith('.') and file.split('.')[-1].lower() in allow_types:
            uncached.append(Document(os.path.join(dir_path, file)))

    if subcache_threshold is not None and len(uncached) > subcache_threshold:
        cache_path = _save_index_to_cache(os.path.join(dir_path, ".recollect"), uncached, child_cache_paths=children_cache_paths)
        
        # reset children paths to just this, as further children are already referenced in this cache level
        children_cache_paths = [cache_path]
        
        # update our bookeeping
        cached += uncached
        uncached = []


    return cached, uncached, children_cache_paths




def get_index(dir_path: str, allow_types: Optional[Tuple[str]] = ('pdf', 'png', 'jpg', 'txt'), use_cache: bool=True, subcache_threshold: Optional[int]=50) -> List[Document]:
    """
    Create an index of documents from the specified directory.
    If use_cache is True, this will save the index to a .recollect subdirectory and load from it for faster index creation in future calls.
    If subcache_threshold is set, any directory with more than this number of files will have its own .recollect cache,
    referenced recursively py parent .recollect caches; use subcache_threshold=None to only use a single cache at dir_path level.
    """

    # check if cached index exists at this level
    if use_cache and os.path.exists(os.path.join(dir_path, '.recollect')):
        documents = _load_cached_index(os.path.join(dir_path, '.recollect'))

        # only return if the cache contained contents
        if len(documents) > 0:
            return documents
        
    # otherwise, depth-first traverse directories to build index
    cached_docs, uncached_docs, child_cache_paths = _create_index_recursive(dir_path=dir_path, allow_types=allow_types, use_cache=use_cache, subcache_threshold=subcache_threshold)

    if use_cache and len(uncached_docs) > 0:
        _save_index_to_cache(os.path.join(dir_path, ".recollect"), uncached_docs, child_cache_paths=child_cache_paths)
        return cached_docs + uncached_docs
    
    return cached_docs + uncached_docs
    

def run_tests():
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests", "data")
    filepaths = extract_file_paths(test_data_dir, ('txt','png'))
    filenames = [os.path.basename(fp) for fp in filepaths]
    for filename in ["construction_project.txt", "dog.txt", "horse.txt", "programmer.txt", "rocket.png", "scene1.png"]:
        assert filename in filenames, f"{filename} not found in extracted file paths"

    documents = get_index(test_data_dir, allow_types=('txt', 'png'), use_cache=False)

    query = "A person who writes code"
    results = search_documents(query, documents, top_k=1)
    assert len(results) == 1
    assert results[0].path.endswith("programmer.txt")

    query = "animal"
    results = search_documents(query, documents, top_k=2)
    assert len(results) == 2
    assert results[0].path.endswith("dog.txt") or results[0].path.endswith("horse.txt")
    assert results[1].path.endswith("dog.txt") or results[1].path.endswith("horse.txt")

    # test for image results
    query = "a rocket"
    results = search_documents(query, documents, top_k=3)
    assert len(results) == 3
    assert results[0].path.endswith("rocket.png")


if __name__ == "__main__":
    run_tests()
    
