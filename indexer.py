import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid

model = SentenceTransformer("all-MiniLM-L6-v2")

client = QdrantClient(path="data/qdrant_db")

COLLECTION = "codebase"


if client.collection_exists(COLLECTION):
    client.delete_collection(COLLECTION)

client.create_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(
        size=384,
        distance=Distance.COSINE
    ),
)

def index_codebase(path):

    points = []

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):

                file_path = os.path.join(root, file)

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                embedding = model.encode(content).tolist()

                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            "file": file_path,
                            "content": content
                        }
                    )
                )

    client.upsert(collection_name=COLLECTION, points=points)

    print("✅ Indexing complete")   

if __name__ == "__main__":
    index_codebase("D:/log_analyzer_ex_app/mini-commerce")