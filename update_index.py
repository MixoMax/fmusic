import tensorflow as tf
import tensorflow_hub as tf_hub
import numpy as np
import librosa

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

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


def get_embeddings(file_path: str) -> list[float]:
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
    embeddings = get_embeddings(song.abs_path)
    
    for vector in embeddings:
        point = PointStruct(id = song.id, vector=vector, payload=song.to_json())
        op = client.upsert(
            collection_name="fmusic",
            points=[point]
        )

def song_is_in_vector_db(song: fcore.SongEntry):
    idx = song.id
    
    res = client.retrieve(
        collection_name="fmusic",
        ids=[idx]
    ) #-> [PointStruct]
    
    return len(res) > 0
        

def update_index():
    
    
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
    
    
    
    
    print("(2/2) Adding songs to vector database for similarity search")
    
    
    num_songs = len(db.get_all_songs())
    for idx, song in enumerate(db.get_all_songs()):
        if not song_is_in_vector_db(song):
            print(f"Adding {song.name} to vector database ({idx}/{num_songs})", end="\r")
            add_song_to_vector_db(song)
        else:
            print(f"Indexed {idx}/{num_songs} songs", end="\r")
            
    
    
    
    

if __name__ == "__main__":
    host = "192.168.178.68:6333"
    client = QdrantClient(host=host)
    
    vector_config = VectorParams(size=521, distance=Distance.COSINE)
    
    model_url = "https://tfhub.dev/google/yamnet/1"
    model = tf_hub.load(model_url)
    
    update_index()