#%% Importing libraries
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn

#for parsing mp3 metadata
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

import Levenshtein as lev

import time
import dataclasses
import sqlite3
import os

#%% Data Setup

def get(_dict,key,default) -> tuple[bool,any]:
    try:
        return True, _dict[key]
    except: #noqa
        return False, default

@dataclasses.dataclass
class Song:
    name:str
    bpm:int
    length:int #in seconds
    kbps:int #kilobits per second
    genre:str
    artist:str
    album:str
    album_art:bytes
    abs_path:str
    
    def save_to_db(self,conn):
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO songs VALUES (?,?,?,?,?,?,?,?, ?)",(self.name,self.bpm,self.length,self.kbps,self.genre,self.artist,self.album,self.album_art,self.abs_path))
            conn.commit()
        except Exception as e:
            if "UNIQUE" in str(e):
                pass
            else:
                print(e)
                print(self.__dict__)
        cursor.close()
    
    def get_metadata(self):
        #print(self.abs_path)
        
        #read metadata from file
        audio = MP3(self.abs_path,ID3=ID3)
        try:
            audio.add_tags()
        except error:
            pass
        
        info_dict = audio.tags
        
        #print(info_dict.keys()) # ['TIT2', 'TPE1', 'TALB', 'TCON', 'TRCK', 'APIC:text_c_03']
        
        #TIT2: -> name
        #TPE1: -> artist
        #TALB: -> album
        #TCON: -> genre
        #TRCK: -> track number
        #APIC: -> album art
        
        self.length = int(audio.info.length)
        self.kbps = int(audio.info.bitrate/1000)
        
        success, self.name = get(info_dict,"TIT2","")
        if success:
            self.name = self.name.text[0]
        
        success, self.artist = get(info_dict,"TPE1","")
        if success:
            self.artist = self.artist.text[0]
        
        success, self.album = get(info_dict,"TALB","")
        if success:
            self.album = self.album.text[0]
        
        success, self.genre = get(info_dict,"TCON","")
        if success:
            try:
                self.genre = self.genre.text[0]
            except:
                self.genre = ""
                
        success, self.album_art = get(info_dict,"APIC",b"")
        if success:
            self.album_art = self.album_art.data
        
        success, self.bpm = get(info_dict,"TBPM",0)
        if success:
            self.bpm = int(self.bpm.text[0])



conn = sqlite3.connect("./music.db")
cursor = conn.cursor()
cmd = """CREATE TABLE IF NOT EXISTS songs (
    name text UNIQUE,
    bpm int,
    length int,
    kbps int,
    genre text,
    artist text,
    album text,
    album_art blob,
    abs_path text UNIQUE
)
    """
cursor.execute(cmd)
conn.commit()

cmd = "SELECT MAX(rowid) FROM songs"
cursor.execute(cmd)
max_id = cursor.fetchone()[0]
print(max_id)
cursor.close()

MUSIC_DIR = "D:\Music"


def is_music_file(file):
    file_endings = [".mp3",".wav"]
    for ending in file_endings:
        if file.endswith(ending):
            return True
    return False

#one time setup
i = 0
files_to_process = 0
t_start = time.time()

for root, dirs, files in os.walk(MUSIC_DIR):
    for file in files:
        if is_music_file(file):
            files_to_process += 1

t_end = time.time()
print(f"Found {files_to_process} files in {t_end-t_start} seconds")

#temp fix:
max_id = 1_000_000

if files_to_process > max_id:
    for root, dirs, files in os.walk(MUSIC_DIR):
        for file in files:
            if is_music_file(file):
                song_path = os.path.join(root,file)
                song = Song(file,0,0,0,"","","", b"", song_path)
                song.get_metadata()
                song.save_to_db(conn)
            
            print(f"Processed {i} of {files_to_process} files")
            i += 1

conn.close()


#%% API Setup
app = FastAPI()

@app.get("/",response_class=HTMLResponse)
def index():
    return FileResponse("index.html")

@app.get("/song_info")
def song_info(name:str):
    conn = sqlite3.connect("./music.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM songs WHERE name = ?",(name,))
    song = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if song is None:
        return JSONResponse({"error":"song not found"})
    
    song = Song(*song)
    out_json = {}
    for key, value in song.__dict__.items():
        if type(value) == bytes:
            out_json[key] = value.decode("utf-8")
        else:
            out_json[key] = value
    
    return JSONResponse(out_json)


def find_closest_matches(search_str, arr, n_results) -> list[tuple[int,str]]: #list of tuples (distance, str)
    #find closest matches to search_str in arr
    #return n_results closest matches
    
    #for each item in arr, calculate the levenshtein distance to search_str
    
    weights = ( 1, 2, 1
        ) #insertion, deletion, substitution
    
    distance_dict = {} #str:distance
    for item in arr:
        distance_dict[item] = lev.distance(search_str,item,weights=weights)
    
    #sort distance_dict by value
    sorted_dict = sorted(distance_dict.items(), key=lambda x: x[1])
    
    #return the first n_results items
    return [(item[1],item[0]) for item in sorted_dict[:n_results]]

@app.get("/search")
def search(q:str):
    #search through all database rows except album art
    #doesnt have to be exact match
    #get the closest match
    
    conn = sqlite3.connect("./music.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM songs")
    names = cursor.fetchall()
    names = [name[0] for name in names]
    
    cursor.execute("SELECT artist FROM songs")
    artists = cursor.fetchall()
    artists = [artist[0] for artist in artists]
    
    cursor.execute("SELECT album FROM songs")
    albums = cursor.fetchall()
    albums = [album[0] for album in albums]
    
    cursor.execute("SELECT genre FROM songs")
    genres = cursor.fetchall()
    genres = [genre[0] for genre in genres]
    
    cursor.close()
    conn.close()
    
    closest = []
    closest.extend(find_closest_matches(q,names,5))
    closest.append("artist")
    closest.extend(find_closest_matches(q,artists,5))
    closest.append("album")
    closest.extend(find_closest_matches(q,albums,5))
    closest.append("genre")
    closest.extend(find_closest_matches(q,genres,5))
    
    #filter out duplicates and empty strings
    out_arr = []
    current_type = "song name"
    for item in closest:
        if type(item) == str:
            current_type = item
            continue
        if item in out_arr:
            continue
        if item[1] == "":
            continue
        item = {"name":item[1], "distance":item[0], "type":current_type}
        out_arr.append(item)
    
    #sort by distance
    out_arr = sorted(out_arr, key=lambda x: x["distance"])
    
    return JSONResponse({"results":out_arr})

@app.get("/song")
def song(name:str):
    conn = sqlite3.connect("./music.db")
    cursor = conn.cursor()
    cursor.execute("SELECT abs_path FROM songs WHERE name = ?",(name,))
    abs_path = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    return FileResponse(abs_path)

uvicorn.run(app,host="127.0.0.1", port=80)