from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

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


@dataclass
class PlaylistEntry:
    id:int
    name:str
    playlist_art:bytes
    songs:list[SongEntry]
    
    def __str__(self) -> str:
        return f"{self.name} ({len(self.songs)} songs)"


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
        self.conn.commit()
        
    
    def get_num_entries(self, table_name: str = "songs") -> int:
        cmd = F"SELECT MAX(id) FROM {table_name}"
        self.cursor.execute(cmd)
        return self.cursor.fetchone()[0]

    def get_songs(self, mode: str = "AND", limit: int = 10, **restraints) -> list[SongEntry]:
        options = ["id", "bpm", "length", "kbps", "genre", "artist", "album"]
        mode_options = ["AND", "OR"]
        
        restraints = {key: value for key, value in restraints.items() if key in options}
        mode = mode.upper()
        if mode not in mode_options:
            raise ValueError(F"Invalid mode {mode}. Must be one of {mode_options}")
        
        
        songs = None
        for key, value in restraints.items():
            
            if type(value) in [list, tuple]:
                val, upper_limit = value
            else:
                val, upper_limit = value, None
            
            match key:
                case "id":
                    new_songs = self.get_songs_by_id(val, limit, upper_limit)
                case "bpm":
                    new_songs = self.get_songs_by_bpm(val, limit, upper_limit)
                case "length":
                    new_songs = self.get_songs_by_length(val, limit, upper_limit)
                case "kbps":
                    new_songs = self.get_songs_by_kbps(val, limit, upper_limit)
                case "genre":
                    new_songs = self.get_songs_by_genre(val, limit)
                case "artist":
                    new_songs = self.get_songs_by_artist(val, limit)
                case "album":
                    new_songs = self.get_songs_by_album(val, limit)
                case _:
                    raise ValueError(F"Invalid key {key}. Must be one of {options}")
            
            if songs is None:
                songs = set(new_songs)
            else:
                if mode == "AND":
                    songs = songs.intersection(new_songs)
                elif mode == "OR":
                    songs = songs.union(new_songs)
            
        return list(songs)
        
                        
                
    
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
        songs = [self.get_song(song_id) for song_id in songs]
        
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



db = DataBase()

songs = db.get_songs(
    mode = "AND",
    limit = 10000,
    artist = "Elton John",
    album = "Goodbye Yellow Brick Road"
)

for song in songs:
    print(song)