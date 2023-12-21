from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4 as M4A
from mutagen.wave import WAVE

import os


MUSIC_DIR = "D:/Music"

def get_metadata(abs_path) -> dict:
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
    except:
        abs_path = os.path.abspath(abs_path)
        
        name = os.path.basename(abs_path)
        name = name.split(".")[:-1]
        
        file_extension = abs_path.split(".")[-1]
        if file_extension == "flac":
            #we know that flac files usualy dont have the name in the metadata
            pass
        else:
            print("no name found, using filename:", name, "file_extension:", file_extension)

    
    try:
        artist = info_dict["TPE1"].text[0]
    except:
        artist = "Unknown"
    
    try:
        album = info_dict["TALB"].text[0]
    except:
        album = "Unknown"

        
    try:
        genre = info_dict["TCON"].text[0]
    except:
        genre = "Unknown"

        
    try:
        album_art = info_dict["APIC"].data
        album_art = bytes(album_art)
    except:
        album_art = b""
    
    try:
        bpm = info_dict["TBPM"][0]
    except:
        bpm = 0
        
    #{
    #    "name": name,
    #    "artist": artist,
    #    "album": album,
    #    "genre": genre,
    #    "bpm": bpm,
    #    "length": length,
    #    "kbps": kbps,
    #    "album_art": album_art
    #}
    
    return {
        "name": name,
        "artist": artist,
        "album": album,
        "genre": genre,
        "bpm": bpm,
        "length": length,
        "kbps": kbps,
        "album_art": album_art
    }