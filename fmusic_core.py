#fmusic Core
#Author: Linus Horn

from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4 as M4A
from mutagen.wave import WAVE

import librosa
import numpy as np
import matplotlib.pyplot as plt
import PIL.Image as Image

from dataclasses import dataclass

import sqlite3
import os
import io
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))


MUSIC_DIR = "D:/Music"


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

def is_music(file_path: str) -> bool:
    file_extension = file_path.split(".")[-1]
    return file_extension in ["mp3", "wav", "flac", "m4a", "ogg"]

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
        data = self.cursor.fetchone()
        if data is None:
            return None
        else:
            return SongEntry(*data)
    
    def get_songs_by_id(self, song_id: int, limit: int = 10, upper_limit: int = None) -> list[SongEntry]:
        if upper_limit is None:
            cmd = F"SELECT * FROM songs WHERE id={song_id} LIMIT {limit}"
        else:
            cmd = F"SELECT * FROM songs WHERE id BETWEEN {song_id} AND {upper_limit} LIMIT {limit}"
        self.cursor.execute(cmd)
        return [SongEntry(*song) for song in self.cursor.fetchall()]
    
    def get_song_by_name(self, song_name: str) -> SongEntry:
        cmd = "SELECT * FROM songs WHERE name=(?)"
        self.cursor.execute(cmd, (song_name,))
        data = self.cursor.fetchone()
        if data is None:
            return None
        else:
            return SongEntry(*data)
    
    def get_song_by_path(self, song_path: str) -> SongEntry:
        cmd = F"SELECT * FROM songs WHERE abs_path='{song_path}'"
        self.cursor.execute(cmd)
        data = self.cursor.fetchone()
        if data is None:
            return None
        else:
            return SongEntry(*data)
    
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

def dict_to_SongEntry(data: dict) -> SongEntry:
    return SongEntry(
        data["id"],
        data["name"],
        data["abs_path"],
        data["bpm"],
        data["length"],
        data["kbps"],
        data["genre"],
        data["artist"],
        data["album"],
        data["album_art"]
    )


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
        file_name = os.path.basename(abs_path)
        name = os.path.splitext(file_name)[0]
        
    
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
        "id": 0, #id is set by db
        "name": str(name),
        "artist": str(artist),
        "album": str(album),
        "genre": str(genre),
        "bpm": cast_to_int(bpm),
        "length": cast_to_int(length),
        "kbps": cast_to_int(kbps),
        "album_art": bytes(album_art),
        "abs_path": abs_path
    }

def calculate_spectrogram(song:SongEntry) -> os.PathLike:
    img_path = f"./temp/{song.id}.png"
    
    if os.path.exists(img_path):
        return img_path
    
    audio, sr = librosa.load(song.abs_path)
    
    #calculate spectrogram
    S = librosa.feature.melspectrogram(y=audio, sr=sr)
    S_dB = librosa.power_to_db(S, ref=np.max)
    
    #plot spectrogram
    fig = plt.figure(figsize=(8,1))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.imshow(S_dB, origin="lower", aspect="auto", cmap="magma")
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    buf.seek(0)
    
    #close fig
    plt.close(fig)
    
    
    #convert to numpy array
    img = Image.open(buf)
    img = np.array(img)
    
    r1, g1, b1 = 255, 255, 255 # Original value
    r2, g2, b2 = 0, 0, 0 # Value that we want to replace it with
    red, green, blue = img[:,:,0], img[:,:,1], img[:,:,2]
    mask = (red == r1) & (green == g1) & (blue == b1)
    img[:,:,:3][mask] = [r2, g2, b2]
    
    img = Image.fromarray(img)
    
    #save spectrogram
    img_path = f"./temp/{song.id}.png"
    img.save(img_path)
    
    return img_path