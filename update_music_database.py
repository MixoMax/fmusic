import os
import sqlite3
from main import DataBase, SongEntry

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.m4a import M4A
from mutagen.wave import WAVE



MUSIC_DIR = "D:/Music"

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


#delete all temporary spectograms
for file in os.listdir("./temp"):
    if file.endswith(".png"):
        os.remove(os.path.join("./temp", file))


def is_song(filename):
    file_endings = [".mp3", ".wav", ".flac", ".m4a", ".ogg"]
    for ending in file_endings:
        if filename.endswith(ending):
            return True
    else:
        return False

def get_metadata(abs_path) -> SongEntry:
    #use mutagen to get metadata
    
    file_extension = abs_path.split(".")[-1]
    
    match file_extension:
        case "mp3":
            audio = MP3(abs_path)
        case "wav":
            audio = WAVE(abs_path)
        case "flac":
            audio = FLAC(abs_path)
        case "m4a":
            audio = M4A(abs_path)
        case "ogg":
            audio = OggVorbis(abs_path)
        case _:
            raise Exception("Unknown file extension", file_extension)
    
    info_dict = audio.tags
    
    #print(info_dict.keys()) # ['TIT2', 'TPE1', 'TALB', 'TCON', 'TRCK', 'APIC:text_c_03']

    #TIT2: -> name
    #TPE1: -> artist
    #TALB: -> album
    #TCON: -> genre
    #TRCK: -> track number
    #APIC: -> album art
    
    length = int(audio.info.length)
    kbps = int(audio.info.bitrate/1000)
    
    try:
        name = info_dict["TIT2"][0]
    except KeyError:
        name = abs_path.split("\\")[-1]
        #remove file extension
        name =".".join(name.split(".")[:-1])
        print("No name for", abs_path, "setting to", name)
    except IndexError:
        name = abs_path.split("\\")[-1]
        name =".".join(name.split(".")[:-1])
    
    try:
        artist = info_dict["TPE1"].text[0]
    except KeyError:
        artist = "Unknown"
    except IndexError:
        artist = "Unknown"
    
    try:
        album = info_dict["TALB"].text[0]
    except KeyError:
        album = "Unknown"
    except IndexError:
        album = "Unknown"
        
    try:
        genre = info_dict["TCON"].text[0]
    except KeyError:
        genre = "Unknown"
    except IndexError:
        genre = "Unknown"
        
    try:
        album_art = info_dict["APIC"].data
        album_art = bytes(album_art)
    except KeyError:
        album_art = b""
    
    try:
        bpm = info_dict["TBPM"][0]
    except KeyError:
        bpm = 0
    
    return SongEntry(0, name, abs_path, bpm, length, kbps, genre, artist, album, album_art)


num_entries_before = db.get_num_entries()
print("Num entries before:", num_entries_before)


num_files_to_go = 0
for root, dirs, files in os.walk(MUSIC_DIR):
    for filename in files:
        if is_song(filename):
            num_files_to_go += 1


i = 0
for root, dirs, files in os.walk(MUSIC_DIR):
    for filename in files:
        if is_song(filename):
            abs_path = os.path.join(root, filename)
            song_entry = get_metadata(abs_path)
            try:
                db.add_song(song_entry, id_is_auto_increment=True)
            except sqlite3.IntegrityError:
                #print("Duplicate song entry:", song_entry)
                pass
            
            i += 1
            print(f"Added {i}/{num_files_to_go}", end="\r")


num_entries_after = db.get_num_entries()
print("Num entries after:", num_entries_after)
print("Added", num_entries_after - num_entries_before, "entries")