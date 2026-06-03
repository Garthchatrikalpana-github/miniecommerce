from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from llm_client import LLMClient

model = SentenceTransformer("all-MiniLM-L6-v2")
_qdrant = None

def get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(path="data/qdrant_db")
    return _qdrant
llm = LLMClient()

COLLECTION = "codebase"


def extract_error(log_text):

    lines = log_text.split("\n")

    for line in lines:
        if "ERROR" in line or "Exception" in line:
            return line

    return log_text[:500]


# def search_code(query):

#     embedding = model.encode(query).tolist()

#     results = qdrant.query_points(
#         collection_name=COLLECTION,
#         query=embedding,
#         limit=3
#     )
#     print("🔍 Search Results:")
#     print(results)

#     matches = []

#     for point_id, score in results:
#         record = qdrant.retrieve(
#             collection_name=COLLECTION,
#             ids=[point_id]
#         )[0]

#         matches.append(record.payload)

#     return matches

def search_code(query):

    qdrant = get_qdrant()   # ✅ ADD THIS LINE

    embedding = model.encode(query).tolist()

    results = qdrant.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=6
    )

    matches = []

    for point in results.points:
        matches.append({
            "file": point.payload.get("file"),
            "content": point.payload.get("content"),
            "score": point.score
        })

    return matches

def analyze_logs(log_text):

    error = extract_error(log_text)

    code_context = search_code(error)

    prompt = f"""
You are a debugging expert.

ERROR:
{error}

CODE:
{code_context}

Give:
1. Root Cause
2. Fix
3. Explanation
"""

    response = llm.generate(prompt)

    return error, code_context, response
