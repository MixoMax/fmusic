import numpy as np
import librosa



import fmusic_core as fcore

import sqlite3
import os

MUSIC_DIR = fcore.MUSIC_DIR

db = fcore.DataBase()

def add_song_to_index(song_path):
    song_path = os.path.abspath(song_path)
    
    #fetch metadata
    #add to db
    #calculate spectrogram
    
    try:
        metadata = fcore.get_metadata(song_path)
        song = fcore.dict_to_SongEntry(metadata)
    except:
        return False, None
    
    #search for song in db
    #if not found, add to db
    
    try:
        db.add_song(song)
        
        song = db.get_song_by_name(song.name)
        
        fcore.calculate_spectrogram(song)
        return True, song
    except sqlite3.IntegrityError:
        return False, song


def setup_vector_db():
    import tensorflow as tf #noqa
    import tensorflow_hub as tf_hub #noqa
    
    global client, model, vector_config
    
    
    from qdrant_client import QdrantClient #noqa
    from qdrant_client.http.models import Distance, VectorParams, PointStruct #noqa
    
    host = "127.0.0.1:6333"
    client = QdrantClient(host=host) #noqa
    
    vector_config = VectorParams(size=521, distance=Distance.COSINE) #noqa
    
    model_url = "https://tfhub.dev/google/yamnet/1"
    model = tf_hub.load(model_url) #noqa

def get_embeddings(file_path: str) -> list[float]:
    global client, model, vector_config
    
    audio, sr = librosa.load(file_path, sr=None, mono=True)
    embeddings = model(audio)
    #embeddings: [tensorflow.python.framework.ops.EagerTensor, tensorflow.python.framework.ops.EagerTensor, tensorflow.python.framework.ops.EagerTensor]
    #first tensor is the embeddings
    #second tensor is the spectrogram
    #third tensor is the log mel spectrogram
    
    #convert embeddings to numpy array
    embeddings = np.array(embeddings[0])
    
    #convert numpy array to list
    embeddings = embeddings.tolist()
    return embeddings

def add_song_to_vector_db(song: fcore.SongEntry):
    global client, model, vector_config
    
    embeddings = get_embeddings(song.abs_path)
    
    for vector in embeddings:
        point = PointStruct(id = song.id, vector=vector, payload=song.to_json())
        op = client.upsert(
            collection_name="fmusic",
            points=[point]
        )

def song_is_in_vector_db(song: fcore.SongEntry):
    global client, model, vector_config
    
    idx = song.id
    
    res = client.retrieve(
        collection_name="fmusic",
        ids=[idx]
    ) #-> [PointStruct]
    
    return len(res) > 0
        

def update_index(use_vector_db=True):
    
    
    print("(0/2) counting songs to index")
    
    num_songs_to_index = 0
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
            if fcore.is_music(file):
                num_songs_to_index += 1
    
    
    print("(1/2) Adding songs to database")
    
    idx = 0
    new_songs = 0
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
             if fcore.is_music(file):
                is_new, song = add_song_to_index(os.path.join(root, file))
                idx += 1
                
                
                if is_new:
                    new_songs += 1
                
                
                print(f"Indexed {idx}/{num_songs_to_index} songs", end="\r")

    print(f"Indexed {idx} songs")
    print(f"Added {new_songs} new songs")
    
    
    if use_vector_db == False:
        return 0
    
    global client, model, vector_config
    

    print("(2/2) Adding songs to vector database for similarity search")
    
    
    num_songs = len(db.get_all_songs())
    for idx, song in enumerate(db.get_all_songs()):
        if not song_is_in_vector_db(song):
            print(f"Adding {song.name} to vector database ({idx}/{num_songs})", end="\r")
            add_song_to_vector_db(song)
        else:
            print(f"Indexed {idx}/{num_songs} songs", end="\r")
            
    
    
    
    

if __name__ == "__main__":
    
    use_vector_db = input("Use vector database? (y/n): ")
    if use_vector_db == "y":
        setup_vector_db()
        update_index()
    else:
        update_index(False)