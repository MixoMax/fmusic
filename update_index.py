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
        return False
    
    #search for song in db
    #if not found, add to db
    
    try:
        db.add_song(song)
        
        song = db.get_song_by_name(song.name)
        
        fcore.calculate_spectrogram(song)
        return True
    except sqlite3.IntegrityError:
        return False

def update_index():
    
    num_songs_to_index = 0
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
            if fcore.is_music(file):
                num_songs_to_index += 1
    
    
    idx = 0
    new_songs = 0
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
             if fcore.is_music(file):
                is_new = add_song_to_index(os.path.join(root, file))
                idx += 1
                
                if is_new:
                    new_songs += 1
                
                print(f"Indexed {idx}/{num_songs_to_index} songs", end="\r")

    print(f"Indexed {idx} songs")
    print(f"Added {new_songs} new songs")

if __name__ == "__main__":
    update_index()