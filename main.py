from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.requests import Request
import uvicorn

import fmusic_core as fcore

import os
import random
import datetime

db = fcore.DataBase()
app = FastAPI()

MUSIC_DIR = fcore.MUSIC_DIR


#html + frontend
@app.get("/")
async def index():
    with open("./static/index.html", "r") as f:
        html = f.read()
    return HTMLResponse(html)

@app.get("/song/random")
async def random_song_player():
    song_id = random.randint(1, db.get_num_entries())
    
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
    
    new_params = fcore.save_eval(params)
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
    
    playlist = fcore.PlaylistEntry(0, playlist_name, None, songs)
    
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
    
    playlist = fcore.PlaylistEntry(0, "Search Results", None, songs)
    
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
async def full_text_search(q:str) -> list[fcore.SongEntry]:
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



@app.get("/api/spectrogram/{song_id}")
def get_spectrogram(song_id: int) -> FileResponse:
    #calculate spectrogram image
    song = db.get_song_by_id(song_id)
    image_path = fcore.calculate_spectrogram(song)
    return FileResponse(image_path)


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
