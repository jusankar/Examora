from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

def similarity_score(answer, expected):
    emb1 = model.encode(answer, convert_to_tensor=True)
    emb2 = model.encode(expected, convert_to_tensor=True)
    return float(util.cos_sim(emb1, emb2))