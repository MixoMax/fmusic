import os
import openl3
import soundfile as sf
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)


def get_vector(file_path) -> list[list[float]]:
    #calculate vector representation of audio file
    
    audio, sampling_rate = sf.read(file_path)
    embeddings, timestamps = openl3.get_audio_embedding(audio, sr=sampling_rate)
    
    #print(embeddings.shape)
    
    return embeddings.tolist()

def search_db(vector, n_results=5):
    #search db for similar vectors
    
    r = client.search(
        collection_name="songs",
        query_vector=vector,
        limit = n_results
    )
    return r

fp = r"C:\Users\Linus\Music\D\soulseek\complete\Tak-MK\Pokémon\Black & White 2\Disc 1\41. Join Avenue - Level Up #1.mp3"
fp = os.path.abspath(fp)
vec = get_vector(fp)[0]

r = search_db(vec, 5)

print(r)