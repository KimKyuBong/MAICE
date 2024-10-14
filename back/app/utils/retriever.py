import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

class Retriever:
    def __init__(self, documents, doc_embeddings, file_names):
        self.documents = documents
        self.doc_embeddings = doc_embeddings
        self.file_names = file_names
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def retrieve_relevant_info(self, query, top_k=2):
        query_embedding = self.model.encode([query])
        similarities = cosine_similarity(query_embedding, self.doc_embeddings)[0]
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        return [(self.documents[i], self.file_names[i]) for i in top_indices]