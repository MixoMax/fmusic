import os
import sqlite3
from main import DataBase, SongEntry
from get_metadata_core import get_metadata, MUSIC_DIR

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4 as M4A
from mutagen.wave import WAVE


os.chdir(os.path.dirname(os.path.abspath(__file__)))





db = DataBase()


#SongEntry:
#id int #just set to 0
#name:str
#abs_path:str
#bpm:int
#length:int #seconds
#kbps:int
#genre:str
#artist:str
#album:str 
#album_art:bytes #if we dont find any, set to empty bytes b""




def is_song(filename):
    
    file_endings = [".mp3", ".wav", ".flac", ".m4a", ".ogg"]
    for ending in file_endings:
        if filename.endswith(ending):
            return True
    else:
        return False


all_songs = db.get_all_songs()

num_before = len(all_songs)

all_paths = set(
    [song.abs_path for song in all_songs]
)



added = 0
for root, dirs, files in os.walk(MUSIC_DIR):
    for file in files:
        if is_song(file):
            abs_path = os.path.join(root, file)
            if "downloading" in abs_path:
                #file is currently being downloaded and cant be opened
                continue
            if abs_path not in all_paths:
                
                try:
                    data = get_metadata(abs_path) #dict
                    
                    song = SongEntry(
                        id=0,
                        name=data["name"],
                        abs_path=abs_path,
                        bpm=data["bpm"],
                        length=data["length"],
                        kbps=data["kbps"],
                        genre=data["genre"],
                        artist=data["artist"],
                        album=data["album"],
                        album_art=data["album_art"]
                    )
                    
                except Exception as e:
                    print(e, abs_path)
                    continue
                try:
                    
                    db.add_song(song)
                    added += 1
                except sqlite3.IntegrityError:
                    continue
                all_paths.add(abs_path)
                
                print(f"Added {added} songs", end="\r")


num_after = len(db.get_all_songs())

print(f"Added {num_after - num_before} songs")
