from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import fmusic_core as fcore

import os
import random
import datetime

db = fcore.DataBase()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)



MUSIC_DIR = fcore.MUSIC_DIR


#React Frontend


@app.get("/")
async def serve_index():
    return FileResponse("./static/index.html")
    
    




@app.get("/static/{file_path}")
async def serve_static(file_path: str):
    return FileResponse(f"./static/{file_path}")

@app.get("/favicon.ico")
async def serve_favicon():
    return FileResponse("./static/music.png")





#API

@app.get("/api/search")
def search(**params):
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
    
    new_params = fcore.save_eval(params)
    
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
def full_text_search(q:str) -> list[fcore.SongEntry]:
    #url = /api/full_search?q=hello
    
    #searches all columns for q
    #returns a list of SongEntry objects
    
    songs = db.full_text_search(q)
    return JSONResponse([song.to_json() for song in songs])

## Songs

@app.get("/api/song/{song_id}")
def get_song(song_id: int):
    song = db.get_song_by_id(song_id)
    return FileResponse(song.abs_path)

@app.get("/api/song/{song_id}/info")
def get_song_info(song_id: int):
    song = db.get_song_by_id(song_id)
    return JSONResponse(song.to_json())

@app.get("/api/song/{song_id}/art")
def get_song_art(song_id: int):
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
    
    data = fcore.get_metadata(abs_path) #dict
    
    song = fcore.SongEntry(
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
    
    
    
    
## Playlists

@app.get("/api/playlist/{playlist_id}")
def get_playlist(playlist_id: int):
    playlist = db.get_playlist(playlist_id)
    return JSONResponse(playlist.to_json())

@app.get("/api/playlist/{playlist_id}/art")
def get_playlist_art(playlist_id: int):
    playlist = db.get_playlist(playlist_id)
    return FileResponse(playlist.playlist_art)

@app.post("/api/playlist/{playlist_id}/add/{song_id}")
def add_to_playlist(playlist_id: int, song_id: int):
    #url: /api/playlist/1/add?song_id=1
    
    db.add_to_playlist(playlist_id, song_id)

@app.post("/api/playlist/create")
def create_playlist(name: str):
    db.create_playlist(name)
    return JSONResponse({"success": True})

@app.delete("/api/playlist/{playlist_id}/delete")
def delete_playlist(playlist_id: int):
    db.delete_playlist(playlist_id)
    return JSONResponse({"success": True})

@app.delete("/api/playlist/{playlist_id}/remove/{song_id}")
def remove_from_playlist(playlist_id: int, song_id: int):
    db.remove_from_playlist(playlist_id, song_id)
    return JSONResponse({"success": True})



@app.get("/api/spectrogram/{song_id}")
def get_spectrogram(song_id: int) -> FileResponse:
    #calculate spectrogram image
    song = db.get_song_by_id(song_id)
    image_path = fcore.calculate_spectrogram(song)
    return FileResponse(image_path)


## general

@app.get("/api/num_songs")
def get_num_songs():
    return JSONResponse({"num_songs": db.get_num_entries()})


@app.get("/api/get_options")
def get_options_for_columns(column_name: str):
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
def get_options_for_columns_new(column_name: str):
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
def get_option_frequency(column_name: str):
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
    
    return JSONResponse({"success": True, "path": "./static/sitemap.xml"})



if __name__ == "__main__":
    print("new version")
    uvicorn.run(app, host="0.0.0.0", port=8675)
