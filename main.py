from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.requests import Request
import uvicorn

import librosa
import numpy as np
import matplotlib.pyplot as plt
import PIL.Image as Image

import datetime

from dataclasses import dataclass

from get_metadata_core import get_metadata, MUSIC_DIR
import zipfile

import sqlite3
import os
import io
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))




def list_str_to_list(list_str: str) -> list:
    return list_str[1:-1].split(", ")

def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False

def save_eval(cmd:str) -> any:
    
    forbidden_strings = [
        "import",
        "__"
    ]
    
    if any([string in cmd for string in forbidden_strings]):
        return None
    else:
        return eval(cmd)


def cast_to_int(value: any) -> int:
    try:
        return int(value)
    except TypeError:
        return 0
    except ValueError:
        return 0

@dataclass
class SongEntry:
    id:int
    name:str
    abs_path:str
    bpm:int
    length:int #in seconds
    kbps:int
    genre:str
    artist:str
    album:str
    album_art:bytes
    
    def __str__(self) -> str:
        return f"{self.name} by {self.artist} from {self.album} ({self.genre})"
    
    def __hash__(self) -> int:
        #we only care about name and abs_path
        return hash((self.name, self.abs_path))
        
    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "abs_path": self.abs_path,
            "bpm": cast_to_int(self.bpm),
            "length": cast_to_int(self.length),
            "kbps": cast_to_int(self.kbps),
            "genre": self.genre,
            "artist": self.artist,
            "album": str(self.album),
        }
        


@dataclass
class PlaylistEntry:
    id:int
    name:str
    playlist_art:bytes
    songs:list[SongEntry]
    
    def __str__(self) -> str:
        return f"{self.name} ({len(self.songs)} songs)"
    
    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "songs": [song.to_json() for song in self.songs]
        }


class DataBase:
    file_path: str = "./music.db"
    
    def __init__(self) -> None:
        self.conn = sqlite3.connect(self.file_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        cmd = """
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            abs_path TEXT UNIQUE NOT NULL,
            bpm INTEGER,
            length INTEGER,
            kbps INTEGER,
            genre TEXT,
            artist TEXT,
            album TEXT,
            album_art BLOB
        );
        """
        self.cursor.execute(cmd)
        
        cmd = """
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            playlist_art BLOB,
            songs TEXT
        );
        """
        self.cursor.execute(cmd)
        
        cmd = """
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY,
            song_id INTEGER UNIQUE NOT NULL
            );
        """
        self.cursor.execute(cmd)
        
        self.conn.commit()
        
    
    def get_num_entries(self, table_name: str = "songs") -> int:
        cmd = F"SELECT MAX(id) FROM {table_name}"
        self.cursor.execute(cmd)
        return self.cursor.fetchone()[0]

    def get_songs(self, mode: str = "AND", limit: int = 10, **restraints) -> list[SongEntry]:
        options = ["id", "bpm", "length", "kbps", "genre", "artist", "album", "name"]
        mode_options = ["AND", "OR"]
        
        restraints = {key: value for key, value in restraints.items() if key in options}
        mode = mode.upper()
        if mode not in mode_options:
            raise ValueError(F"Invalid mode {mode}. Must be one of {mode_options}")
        
        all_songs = self.get_all_songs()
        songs_out = []
        
        for key, value in restraints.items():
            prev_num = len(all_songs)
            
            new_songs = []
            for song in all_songs:
                
                if type(value) == tuple:
                    if song.__dict__[key] >= value[0] and song.__dict__[key] <= value[1]:
                        new_songs.append(song)
                else:
                    if song.__dict__[key] == value:
                        new_songs.append(song)
            
            if mode == "AND": #limit to songs that match all restraints
                all_songs = new_songs
                songs_out = new_songs
            elif mode == "OR":
                songs_out += new_songs
            
            print(key, prev_num, " -> ", len(all_songs))
            
            
        if limit is not None:
            songs_out = list(set(songs_out))[:limit]
        else:
            print("limit is None")
            songs_out = list(set(songs_out))
        
        return songs_out
    
    def get_song_by_id(self, song_id: int) -> SongEntry:
        cmd = F"SELECT * FROM songs WHERE id={song_id}"
        self.cursor.execute(cmd)
        return SongEntry(*self.cursor.fetchone())
    
    def get_songs_by_id(self, song_id: int, limit: int = 10, upper_limit: int = None) -> list[SongEntry]:
        if upper_limit is None:
            cmd = F"SELECT * FROM songs WHERE id={song_id} LIMIT {limit}"
        else:
            cmd = F"SELECT * FROM songs WHERE id BETWEEN {song_id} AND {upper_limit} LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_song_by_name(self, song_name: str) -> SongEntry:
        cmd = F"SELECT * FROM songs WHERE name='{song_name}'"
        self.cursor.execute(cmd)
        return SongEntry(*self.cursor.fetchone())
    
    def get_song_by_path(self, song_path: str) -> SongEntry:
        cmd = F"SELECT * FROM songs WHERE abs_path='{song_path}'"
        self.cursor.execute(cmd)
        return SongEntry(*self.cursor.fetchone())
    
    def get_songs_by_bpm(self, song_bpm: int, limit: int = 10, upper_limit: int = None) -> list[SongEntry]:
        if upper_limit is None:
            cmd = F"SELECT * FROM songs WHERE bpm={song_bpm} LIMIT {limit}"
        else:
            cmd = F"SELECT * FROM songs WHERE bpm BETWEEN {song_bpm} AND {upper_limit} LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_songs_by_length(self, song_length: int, limit: int = 10, upper_limit: int = None) -> list[SongEntry]:
        if upper_limit is None:
            cmd = F"SELECT * FROM songs WHERE length={song_length} LIMIT {limit}"
        else:
            cmd = F"SELECT * FROM songs WHERE length BETWEEN {song_length} AND {upper_limit} LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_songs_by_kbps(self, song_kbps: int, limit: int = 10, upper_limit: int = None) -> list[SongEntry]:
        if upper_limit is None:
            cmd = F"SELECT * FROM songs WHERE kbps={song_kbps} LIMIT {limit}"
        else:
            cmd = F"SELECT * FROM songs WHERE kbps BETWEEN {song_kbps} AND {upper_limit} LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_songs_by_genre(self, song_genre: str, limit: int = 10) -> list[SongEntry]:
        cmd = F"SELECT * FROM songs WHERE genre='{song_genre}' LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_songs_by_artist(self, song_artist: str, limit: int = 10) -> list[SongEntry]:
        cmd = F"SELECT * FROM songs WHERE artist='{song_artist}' LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_songs_by_album(self, song_album: str, limit: int = 10) -> list[SongEntry]:
        cmd = F"SELECT * FROM songs WHERE album='{song_album}' LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_all_songs(self, limit: int = None) -> list[SongEntry]:
        if limit is not None:
            cmd = F"SELECT * FROM songs LIMIT {limit}"
        else:
            cmd = "SELECT * FROM songs"
            
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    
    
    def add_song(self, song: SongEntry, id_is_auto_increment: bool = True) -> None:
        if id_is_auto_increment:
            try:
                song.id = self.get_num_entries() + 1
            except TypeError:
                #table is empty
                song.id = 1
        cmd = "INSERT INTO songs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.cursor.execute(cmd, (song.id, song.name, song.abs_path, song.bpm, song.length, song.kbps, song.genre, song.artist, song.album, song.album_art))
        self.conn.commit()
    
    def delete_song(self, song_id: int) -> None:
        cmd = F"DELETE FROM songs WHERE id={song_id}"
        self.cursor.execute(cmd)
        self.conn.commit()
    
    
    
    def get_playlist(self, playlist_id: int) -> PlaylistEntry:
        cmd = F"SELECT * FROM playlists WHERE id={playlist_id}"
        self.cursor.execute(cmd)
        id, name, playlist_art, songs = self.cursor.fetchone()
        
        songs = list_str_to_list(songs)
        songs = [self.get_song_by_id(int(song_id)) for song_id in songs]
        
        return PlaylistEntry(id, name, playlist_art, songs)
        
    
    def add_playlist(self, playlist: PlaylistEntry) -> None:
        
        song_ids = [song.id for song in playlist.songs]
        song_ids = str(song_ids)
        
        if playlist.playlist_art is None:
            playlist.playlist_art = b"NULL"
        
        cmd = "INSERT INTO playlists VALUES (?, ?, ?, ?)"
        
        self.cursor.execute(cmd, (playlist.id, playlist.name, playlist.playlist_art, song_ids))
        self.conn.commit()
    
    def delete_playlist(self, playlist_id: int) -> None:
        cmd = F"DELETE FROM playlists WHERE id={playlist_id}"
        self.cursor.execute(cmd)
        self.conn.commit()
    
    def update_playlist(self, playlist: PlaylistEntry) -> None:
        id = playlist.id
        cmd = f"UPDATE playlists SET name=?, playlist_art=?, songs=? WHERE id={id}"
        
        song_ids = [song.id for song in playlist.songs]
        song_ids = str(song_ids)
        
        self.cursor.execute(cmd, (playlist.name, playlist.playlist_art, song_ids))
        self.conn.commit()



    def add_to_favorite(self, song_id: int) -> None:
        cmd = "INSERT INTO favorites VALUES (?, ?)"
        self.cursor.execute(cmd, (None, song_id))
        self.conn.commit()
    
    def remove_from_favorite(self, song_id: int) -> None:
        cmd = F"DELETE FROM favorites WHERE song_id={song_id}"
        self.cursor.execute(cmd)
        self.conn.commit()
    
    def get_favorites(self) -> list[SongEntry]:
        cmd = "SELECT * FROM favorites"
        self.cursor.execute(cmd)
        favorites = [self.get_song_by_id(song_id) for _, song_id in self.cursor.fetchall()]
        return favorites
    
    def get_favorite_playlist(self) -> PlaylistEntry:
        favorites = self.get_favorites()
        return PlaylistEntry(0, "Favorites", None, favorites)
    
    def is_favorite(self, song_id: int) -> bool:
        cmd = "SELECT * FROM favorites WHERE song_id=(?)"
        self.cursor.execute(cmd, (song_id,))
        return len(self.cursor.fetchall()) > 0

    
    def full_text_search(self, q: str) -> list[SongEntry]:
        #searches all columns for q
        #returns a list of SongEntry objects
        #that contain q in one of their columns
        
        cmd = F"SELECT * FROM songs WHERE name LIKE '%{q}%' OR abs_path LIKE '%{q}%' OR bpm LIKE '%{q}%' OR length LIKE '%{q}%' OR kbps LIKE '%{q}%' OR genre LIKE '%{q}%' OR artist LIKE '%{q}%' OR album LIKE '%{q}%'"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]

db = DataBase()
app = FastAPI()



#html + frontend
@app.get("/")
async def index():
    with open("./static/index.html", "r") as f:
        html = f.read()
    return HTMLResponse(html)

@app.get("/song/random")
async def random_song_player():
    song_id = np.random.randint(1, db.get_num_entries())
    
    with open("./static/song_player.html", "r") as f:
        html = f.read()
    
    html = html.replace(
        "song_id_placeholder",
        str(song_id)
    )
    
    return HTMLResponse(html)

@app.get("/song/{song_id}")
async def song_player(song_id: int):
    
    with open("./static/song_player.html", "r") as f:
        html = f.read()
        
    song = db.get_song_by_id(song_id)
        
    replacements = {
        "song_id_placeholder": song_id,
        "song_name_placeholder": song.name,
        "song_artist_placeholder": song.artist,
        "song_length_fancy_placeholder": str(datetime.timedelta(seconds=song.length)), #mm:ss
    }
    
    for key, value in replacements.items():
        html = html.replace(key, str(value))
    
    return HTMLResponse(html)

@app.get("/upload")
async def upload_page():
    with open("./static/uploadForm.html", "r") as f:
        html = f.read()
    return HTMLResponse(html)



@app.get("/playlist/{playlist_id}")
async def playlist_player(playlist_id: int):
    if playlist_id == 0:
        #playlist_id 0 is reserved for favorites
        playlist = db.get_favorite_playlist()
    else:
        playlist = db.get_playlist(playlist_id)

    with open("./static/playlist_player.html", "r") as f:
        html = f.read()
    
    html = html.replace(
        '"playlist_data_placeholder"',
        str(playlist.to_json())
    )
    
    return HTMLResponse(html)


#dynamically generated playlist
@app.get("/dynamic_playlist")
async def dynamic_playlist(**params):
    #url = /dynamic_playlist?params={"limit": 10, "mode": "AND", "playlist_name": "Dynamic Playlist", "bpm": (100, 200), "genre": "Rock", "artist": "AC/DC"}
    
    #get playlist by params
    
    params = params["params"] #str
    
    new_params = save_eval(params)
    print(new_params, type(new_params))
    
    
    if "limit" in new_params:
        limit = new_params["limit"]
        del new_params["limit"]
    else:
        limit = None
        
    if "mode" in new_params:
        mode = new_params["mode"]
        del new_params["mode"]
    else:
        mode = "AND"
        
    if "playlist_name" in new_params:
        playlist_name = new_params["playlist_name"]
        del new_params["playlist_name"]
    else:
        playlist_name = "Dynamic Playlist"
    
    
    songs = db.get_songs(**new_params, limit=limit, mode=mode)
    
    #inject songs into playlist_player.html
    with open("./static/playlist_player.html", "r") as f:
        html = f.read()
    
    playlist = PlaylistEntry(0, playlist_name, None, songs)
    
    html = html.replace(
        '"playlist_data_placeholder"',
        str(playlist.to_json())
    )
    
    return HTMLResponse(html)


@app.get("/dynamic_playlist_full_text_search")
async def dynamic_playlist_full_text_search(q: str):
    #url = /dynamic_playlist_full_text_search?q=hello

    songs = db.full_text_search(q)
    
    #inject songs into playlist_player.html
    with open("./static/playlist_player.html", "r") as f:
        html = f.read()
    
    playlist = PlaylistEntry(0, "Search Results", None, songs)
    
    html = html.replace(
        '"playlist_data_placeholder"',
        str(playlist.to_json())
    )
    
    return HTMLResponse(html)




#static files
@app.get("/static/{file_path}")
def serve_static(file_path: str):

    return FileResponse(F"./static/{file_path}")

@app.get("/dynamic/{file_path}/song/{song_id}")
def serve_dynamic_song(file_path: str, song_id: int):
    #load js file
    #inject song data into "song_data_placeholder"
    
    js_str = ""
    with open(F"./static/{file_path}", "r") as f:
        js_str = f.read()
    
    song = db.get_song_by_id(song_id)
    
    js_str = js_str.replace(
        '"song_data_placeholder"',
        str(song.to_json())
    )
    
    header = {
        "Content-Type": "application/javascript"
    }
    
    return HTMLResponse(js_str, headers=header)


#favicon and robot stuff

@app.get("/favicon.ico")
def serve_favicon():
    return FileResponse("./static/music.png")



@app.get("/robots.txt")
def serve_robots():
    return FileResponse("./static/robots.txt")

@app.get("/license.txt")
def serve_license():
    return FileResponse("./static/license.txt")

@app.get("/manifest.json")
def serve_manifest():
    return FileResponse("./static/manifest.json")


@app.get("/sitemap.xml")
def serve_sitemap():
    return FileResponse("./static/sitemap.xml")




#API

@app.get("/api/search")
async def search(**params):
    #param options:
    #limit: int
    #mode: str (AND or OR)
    #bpm: int or tuple (min, max)
    #length: int or tuple (min, max)
    #kbps: int or tuple (min, max)
    #genre: str
    #artist: str
    #album: str
    #name: str
    

    params = params["params"] #str
    
    new_params = save_eval(params)
    
    if "limit" in new_params:
        limit = new_params["limit"]
        del new_params["limit"]
    else:
        limit = 10
    
    if "mode" in new_params:
        mode = new_params["mode"]
        del new_params["mode"]
    else:
        mode = "AND"

    songs = db.get_songs(**new_params, limit=limit, mode=mode)
    print(len(songs))
    return JSONResponse([song.to_json() for song in songs])


@app.get("/api/full_search")
async def full_text_search(q:str) -> list[SongEntry]:
    #url = /api/full_search?q=hello
    
    #searches all columns for q
    #returns a list of SongEntry objects
    
    songs = db.full_text_search(q)
    return JSONResponse([song.to_json() for song in songs])

## Songs

@app.get("/api/song/{song_id}")
async def get_song(song_id: int):
    song = db.get_song_by_id(song_id)
    return FileResponse(song.abs_path)

@app.get("/api/song/{song_id}/info")
async def get_song_info(song_id: int):
    song = db.get_song_by_id(song_id)
    return JSONResponse(song.to_json())

@app.get("/api/song/{song_id}/art")
async def get_song_art(song_id: int):
    song = db.get_song_by_id(song_id)
    return FileResponse(song.album_art)

@app.post("/api/song/upload")
async def upload_song(request: Request) -> JSONResponse:
    #uploads an mp3 file
    #returns success
    
    #get file
    form = await request.form()
    file = form["file"] #UploadedFile
    
    #to bytes
    audio_file = await file.read()
    audio_file = bytes(audio_file)

    
    
    #save file to disk
    file_path = os.path.join(MUSIC_DIR, "download", file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as f:
        print(type(audio_file))
        f.write(audio_file)
    
    abs_path = os.path.abspath(file_path)
    
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
    
    try:
        db.add_song(song)
    except:
        #song already exists
        return JSONResponse({"success": False})
    return JSONResponse({"success": True})

@app.post("/api/song/upload/many")
async def upload_many_songs(request: Request) -> JSONResponse:
    #upload a zip or gzip file containing many mp3 files
    #returns success
    
    print("uploading many songs")
    
    #get file
    form = await request.form()
    file = form["file"] #UploadedFile
    
    #to bytes
    zip_file = await file.read()
    zip_file = bytes(zip_file)
    
    #save file to disk
    file_path = os.path.join(MUSIC_DIR, "download", file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as f:
        f.write(zip_file)
    
    print(1)
    
    #extract zip file
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(os.path.join(os.path.dirname(file_path), file.filename.split(".")[0]))
    
    print(2)
    
    #delete zip file
    os.remove(file_path)
    
    print(3)
    
    #get all files in directory
    files = []
    file_path = os.path.join(os.path.dirname(file_path), file.filename.split(".")[0])
    for root, dirs, files in os.walk(file_path):
        for file in files:
            files.append(os.path.join(root, file))
    
    print(4)
    
    #add all files to database
    for file in files:
        data = get_metadata(file)
        song = SongEntry(
            id=0,
            name=data["name"],
            abs_path=file,
            bpm=data["bpm"],
            length=data["length"],
            kbps=data["kbps"],
            genre=data["genre"],
            artist=data["artist"],  
            album=data["album"],
            album_art=data["album_art"]
        )
        
        try:
            db.add_song(song)
        except:
            #song already exists
            continue
    
    print(5)

    return JSONResponse({"success": True})
    
    
    
    
## Playlists

@app.get("/api/playlist/{playlist_id}")
async def get_playlist(playlist_id: int):
    playlist = db.get_playlist(playlist_id)
    return JSONResponse(playlist.to_json())

@app.get("/api/playlist/{playlist_id}/art")
async def get_playlist_art(playlist_id: int):
    playlist = db.get_playlist(playlist_id)
    return FileResponse(playlist.playlist_art)

@app.get("/api/playlist/{playlist_id}/songs")
async def get_playlist_songs(playlist_id: int):
    playlist = db.get_playlist(playlist_id)
    return JSONResponse([song.to_json() for song in playlist.songs])

## favorites

@app.get("/api/favorites")
async def get_favorites():
    favorites = db.get_favorites()
    return JSONResponse([song.to_json() for song in favorites])

@app.get("/api/favorites/add/{song_id}")
async def add_to_favorites(song_id: int):
    db.add_to_favorite(song_id)
    return JSONResponse({"success": True})

@app.get("/api/favorites/remove/{song_id}")
async def remove_from_favorites(song_id: int):
    db.remove_from_favorite(song_id)
    return JSONResponse({"success": True})

@app.get("/api/favorites/is_favorite/{song_id}")
async def is_favorite(song_id: int):
    return JSONResponse({"is_favorite": db.is_favorite(song_id)})


# spectrogram using librosa
#TODO: make this faster
#maybe generate spectrograms at indexing time but then indexing will take much longer
@app.get("/api/spectrogram/{song_id}")
def get_spectrogram(song_id: int) -> FileResponse:
    #calculate spectrogram image
    t_start = time.time()
    
    file_path = os.path.join(os.getcwd(), f"./temp/{song_id}.png")

    if os.path.exists(file_path):
        #return image
        t_end = time.time()
        print(f"{(t_end - t_start)*1000:.2f} ms")
        return FileResponse(file_path)
    
    song = db.get_song_by_id(song_id)

    
    audio_path = os.path.abspath(song.abs_path)
    
    #load audio
    y, sr = librosa.load(audio_path)
    
    #calculate spectrogram
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    S_dB = librosa.power_to_db(S, ref=np.max)
    
    #convas for image is 800x100
    #so we need to stretch the image to fit and remove the whitespace left and right

    fig = plt.figure(figsize=(8, 1))
    ax = fig.add_subplot(111)
    ax.axis("off")
    #cmap options: https://matplotlib.org/stable/tutorials/colors/colormaps.html
    ax.imshow(S_dB, origin="lower", aspect="auto", cmap="magma")
    
    #save image to disk
    img_path = f"./temp/{song_id}.png"
    
    #load into PIL object
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    buf.seek(0)
    
    #close fig
    plt.close(fig)
    
    
    img = Image.open(buf)
    #make WHITE pixels transparent
    img = img.convert("RGBA")
    data = np.array(img)
    r1, g1, b1 = 255, 255, 255 # Original value
    r2, g2, b2, a2 = 0, 0, 0, 0 # Value that we want to replace it with
    red, green, blue, alpha = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    mask = (red == r1) & (green == g1) & (blue == b1)
    data[:,:,:4][mask] = [r2, g2, b2, a2]
    img = Image.fromarray(data)
    
    #save image
    img.save(img_path)
    print("saved image", img_path)
    
    t_end = time.time()
    print(f"{(t_end - t_start)*1000:.2f} ms")
    #return image
    return FileResponse(img_path)
    


## general

@app.get("/api/get_num_songs")
async def get_num_songs():
    return JSONResponse({"num_songs": db.get_num_entries()})


@app.get("/api/get_options")
async def get_options_for_columns(column_name: str):
    #return a set of all values for a column
    #except for id, abs_path, name and album_art
    if column_name in ["id", "abs_path", "name", "album_art"]:
        return JSONResponse({"options": []})
    
    #other colums:
    #bpm, length, kbps, genre, artist, album
    
    options = set()
    songs = db.get_all_songs()
    
    for song in songs:
        options.add(song.__dict__[column_name])
    
    return JSONResponse({"options": list(options)})

@app.get("/api/get_options_new")
async def get_options_for_columns_new(column_name: str):
    #return a set of all values for a column
    #except for id, abs_path, name and album_art
    if column_name in ["id", "abs_path", "name", "album_art"]:
        return JSONResponse({"options": []})
    
    #other colums:
    #bpm, length, kbps, genre, artist, album
    
    options = set()
    
    max_id = db.get_num_entries()
    
    for i in range(0, max_id, 100):
        songs = db.get_songs_by_id(i, 100, i+100)
        for song in songs:
            options.add(song.__dict__[column_name])
    
    return JSONResponse({"options": list(options)})

@app.get("/api/get_option_frequency")
async def get_option_frequency(column_name: str):
    #return a dict of all values for a column and their frequency
    #except for id, abs_path, name and album_art
    if column_name in ["id", "abs_path", "name", "album_art"]:
        return JSONResponse({"options": []})
    
    #other colums:
    #bpm, length, kbps, genre, artist, album
    
    options = {} #option: count
    songs = db.get_all_songs()
    
    for song in songs:
        value = song.__dict__[column_name]
        if value not in options:
            options[value] = 0
        options[value] += 1
    
    return JSONResponse(options)


@app.get("/api/generate_sitemap")
def generate_sitemap():
    #generate sitemap and save it to disk
    #return success
    
    #generate sitemap
    songs = db.get_all_songs()
    
    sitemap = ""
    sitemap += "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    sitemap += "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    
    #add index page
    url = "https://fmusic.linushorn.dev/"
    
    sitemap += f"""
    <url>
        <loc>{url}</loc>
        <lastmod>{current_timestamp}</lastmod>
    </url>
    """

    routes = [
        "/manifest.json", "/robots.txt", "/license.txt"
    ]
    
    for song in songs:
        routes.append(f"/song/{song.id}")

    for route in routes:
        url = f"https://fmusic.linushorn.dev{route}"
        sitemap += f"""
        <url>
            <loc>{url}</loc>
            <lastmod>{current_timestamp}</lastmod>
        </url>
        """
    
    sitemap += "</urlset>"
    
    #save sitemap
    with open("./static/sitemap.xml", "w") as f:
        f.write(sitemap)
    
    return JSONResponse({"success": True})



if __name__ == "__main__":
    print("new version")
    uvicorn.run(app, host="0.0.0.0", port=8675)
