from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import uvicorn

import os
import random
import datetime

from fmusicCore import DataBase, SongEntry, PlaylistEntry, list_str_to_list, is_int, save_eval, cast_to_int, calculate_spectrogram

os.chdir(os.path.dirname(os.path.abspath(__file__)))




db = DataBase()
app = FastAPI()


#htmx frontend

@app.get("/")
async def index():
    
    html = open("./static/index.html", "r").read()

    return HTMLResponse(html)

@app.get("/htmx/full_search")
async def htmx_full_search(q: str):
    #same as /api/full_search but returns html instead of json
    
    songs = db.full_text_search(q)
    
    html = "<ul>"
    
    for song in songs:
        html += song_to_html(song)
    
    html += "</ul>"
    
    return HTMLResponse(html)

@app.get("/htmx/song/{song_id}")
async def htmx_get_song(song_id: int):
    song = db.get_song_by_id(song_id)
    return song_to_html(song)


def song_to_html(song: SongEntry) -> str:
    
    is_favorite = db.is_favorite(song.id)
    
    print(song.id, is_favorite)
    
    html = f"""
        <li class="song-entry" id="song_{song.id}">
            <div class="song-play-pause">
                <button onclick="play_pause_song({song.id})">play</button>
            </div>
            <div class="song-name">
                {song.name}
            </div>
            <div class="song-artist">
                {song.artist}
            </div>
            <div class="song-album">
                {song.album}
            </div>
            <div class="song-genre">
                {song.genre}
            </div>
            <div class="song-favorite">
                <button onclick="add_remove_favorite({song.id})" class="favorite-button">
                    <img src="/static/heart_{"filled" if is_favorite else "empty"}.svg" alt="favorite" id = "favorite_{song.id}" class="favorite-icon" width="20px" height="20px">
                </button>
            </div>  
        </li>
        """
        
    return html



@app.get("/static/{file_path:path}")
async def static(file_path: str):
    return FileResponse(f"./static/{file_path}")


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
    # -> [{"id", "name", "artist", "album", "genre", "bpm", "length", "kbps", "abs_path", "album_art"}, ...]
    
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

@app.get("/api/favorites/toggle/{song_id}")
async def toggle_favorite(song_id: int):
    is_favorite = db.is_favorite(song_id)
    if is_favorite:
        db.remove_from_favorite(song_id)
    else:
        db.add_to_favorite(song_id)
    return JSONResponse({"success": True, "is_favorite": not is_favorite})

@app.get("/api/favorites/is_favorite/{song_id}")
async def is_favorite(song_id: int):
    return JSONResponse({"is_favorite": db.is_favorite(song_id)})



@app.get("/api/spectrogram/{song_id}")
def get_spectrogram(song_id: int) -> FileResponse:
    file_path = calculate_spectrogram(db, song_id)
    
    return FileResponse(file_path)
    


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
