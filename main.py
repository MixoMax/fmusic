from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.requests import Request
import uvicorn

from dataclasses import dataclass

import sqlite3
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))




def list_str_to_list(list_str: str) -> list:
    return list_str[1:-1].split(", ")
    
    
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
        self.conn = sqlite3.connect(self.file_path)
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
            
            if mode == "AND":
                all_songs = new_songs
            elif mode == "OR":
                pass #dont change all_songs
            
            songs_out += new_songs
            
            print(key, prev_num, " -> ", len(all_songs))
            
            
        
        return list(set(songs_out))[:limit]      
    
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
    song = db.get_song_by_id(song_id)
    
    with open("./static/song_player.html", "r") as f:
        html = f.read()
    
    html = html.replace(
        '"song_data_placeholder"',
        str(song.to_json())
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


#static files
@app.get("/static/{file_path}")
def serve_static(file_path: str):
    return FileResponse(F"./static/{file_path}")




#API

@app.get("/api/search")
async def search(request: Request):
    params = dict(request.query_params)
    print(params)
    songs = db.get_songs(**params)
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

uvicorn.run(app, host="127.0.0.1", port=80)