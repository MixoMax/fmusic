from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn

from dataclasses import dataclass

import sqlite3
import os

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
        "__",
        "os",
        "sys",
        "open"
    ]
    
    if any([string in cmd for string in forbidden_strings]):
        return None
    else:
        return eval(cmd)
    
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
        return hash(f"{self.id}{self.name}{self.abs_path}{self.bpm}{self.length}{self.kbps}{self.genre}{self.artist}{self.album}")
    
    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "abs_path": self.abs_path,
            "bpm": self.bpm,
            "length": self.length,
            "kbps": self.kbps,
            "genre": self.genre,
            "artist": self.artist,
            "album": self.album
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
    
    
    
    def add_song(self, song: SongEntry) -> None:
        cmd = F"""
        INSERT INTO songs VALUES (
            {song.id},
            '{song.name}',
            '{song.abs_path}',
            {song.bpm},
            {song.length},
            {song.kbps},
            '{song.genre}',
            '{song.artist}',
            '{song.album}',
            {song.album_art}
        );
        """
        self.cursor.execute(cmd)
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
    html = """
    <html>
        <head>
            <title>Music API</title>
        </head>
        <body>
            <h1>Music API</h1>
            <p>Created by <a href="https://www.github.com/MixoMax">MixoMax</a></p>
            <p>api documentation at <a href="/docs">/docs</a></p>
        </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/song/{song_id}")
async def song_player(song_id: int):
    
    with open("./static/song_player.html", "r") as f:
        html = f.read()
    
    html = html.replace(
        "song_id_placeholder",
        str(song_id)
    )
    
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

@app.get("/favicon.ico")
def serve_favicon():
    return FileResponse("./static/music.png")




#API

@app.get("/api/search")
async def search(**params):

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


## general

@app.get("/api/get_num_songs")
async def get_num_songs():
    return JSONResponse({"num_songs": db.get_num_entries()})

#TODO these need to be optimized
#currently they take approx 300ms to complete
#this is because they need to go through all songs
#and get the unique values for the column

#possible fixes:
#creata a new table and store all unique values there
#and calculate it at the same time we scrape the songs
#this would make the scraping take longer a little longer but not much
#and the api calls would be much faster

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



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)