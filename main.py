from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

import fmusic_core as fcore

import os
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


#Frontend

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

class SearchParameters(BaseModel):
    limit: int = 10
    mode: str = "AND"
    bpm: int | list[int] = None
    length: int | list[int] = None
    kbps: int | list[int] = None
    genre: str | list[str] = None
    artist: str | list[str] = None
    album: str | list[str] = None
    name: str | list[str] = None


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


@app.post("/api/search_new")
async def search_new(params: SearchParameters):
    #param options:
    #limit: int -> How many songs to return
    #mode: str (AND or OR) -> How to combine the search parameters
    
    #bpm: int | list[int]
    # if int: return songs with bpm == int
    # if list[int]: 
    # if len(list) == 2: return songs with bpm between list[0] and list[1]
    # if len(list) > 2: return songs with bpm in list
    
    #length: int | list[int]
    # Same as bpm
    
    #kbps: int | list[int]
    # Same as bpm
    
    #genre: str | list[str]
    # if str: return songs with genre == str
    # if list[str]: return songs with genre in list
    
    #artist: str | list[str]
    # Same as genre
    
    #album: str | list[str]
    # Same as genre
    
    #name: str | list[str]
    # Same as genre
    
    #return a list of SongEntry.to_json()
    
    
    songs = db.get_all_songs()
    
    songs_out = set()
    
    print(params)
    
    
    if params.mode == "OR":
        
        if type(params.bpm) == int:
            for song in songs:
                if song.bpm == params.bpm:
                    songs_out.add(song)
        else:
            if len(params.bpm) == 2:
                for song in songs:
                    if song.bpm >= params.bpm[0] and song.bpm <= params.bpm[1]:
                        songs_out.add(song)
            else:
                for song in songs:
                    if song.bpm in params.bpm:
                        songs_out.add(song)
        
        if type(params.length) == int:
            for song in songs:
                if song.length == params.length:
                    songs_out.add(song)
        else:
            if len(params.length) == 2:
                for song in songs:
                    if song.length >= params.length[0] and song.length <= params.length[1]:
                        songs_out.add(song)
            else:
                for song in songs:
                    if song.length in params.length:
                        songs_out.add(song)
        
        if type(params.kbps) == int:
            for song in songs:
                if song.kbps == params.kbps:
                    songs_out.add(song)
        else:
            if len(params.kbps) == 2:
                for song in songs:
                    if song.kbps >= params.kbps[0] and song.kbps <= params.kbps[1]:
                        songs_out.add(song)
            else:
                for song in songs:
                    if song.kbps in params.kbps:
                        songs_out.add(song)
        
        if type(params.genre) == str:
            for song in songs:
                if song.genre == params.genre:
                    songs_out.add(song)
        else:
            for song in songs:
                if song.genre in params.genre:
                    songs_out.add(song)
        
        if type(params.artist) == str:
            for song in songs:
                if song.artist == params.artist:
                    songs_out.add(song)
        else:
            for song in songs:
                if song.artist in params.artist:
                    songs_out.add(song)
        
        if type(params.album) == str:
            for song in songs:
                if song.album == params.album:
                    songs_out.add(song)
        else:
            for song in songs:
                if song.album in params.album:
                    songs_out.add(song)
        
        if type(params.name) == str:
            for song in songs:
                if song.name == params.name:
                    songs_out.add(song)
        else:
            for song in songs:
                if song.name in params.name:
                    songs_out.add(song)
        
    elif params.mode == "AND":
            for song in songs:
                
                if params.bpm != None:
                    if type(params.bpm) == int:
                        if song.bpm != params.bpm:
                            continue
                    else:
                        if len(params.bpm) == 2:
                            if song.bpm < params.bpm[0] or song.bpm > params.bpm[1]:
                                continue
                        else:
                            if song.bpm not in params.bpm:
                                continue
                
                if params.length != None:
                    if type(params.length) == int:
                        if song.length != params.length:
                            continue
                    else:
                        if len(params.length) == 2:
                            if song.length < params.length[0] or song.length > params.length[1]:
                                continue
                        else:
                            if song.length not in params.length:
                                continue
                
                if params.kbps != None:
                    if type(params.kbps) == int:
                        if song.kbps != params.kbps:
                            continue
                    else:
                        if len(params.kbps) == 2:
                            if song.kbps < params.kbps[0] or song.kbps > params.kbps[1]:
                                continue
                        else:
                            if song.kbps not in params.kbps:
                                continue
                
                if params.genre != None:
                    if type(params.genre) == str:
                        if song.genre != params.genre:
                            continue
                    else:
                        if song.genre not in params.genre:
                            continue
                
                if params.artist != None:
                    if type(params.artist) == str:
                        if song.artist != params.artist:
                            continue
                    else:
                        if song.artist not in params.artist:
                            continue
                
                if params.album != None:
                    if type(params.album) == str:
                        if song.album != params.album:
                            continue
                    else:
                        if song.album not in params.album:
                            continue
                
                if params.name != None:
                    if type(params.name) == str:
                        if song.name != params.name:
                            continue
                    else:
                        if song.name not in params.name:
                            continue
                
                #none of the continue statements were executed
                #so all parameters match
                songs_out.add(song)
    
    
    return JSONResponse([song.to_json() for song in songs_out])
    
    



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





@app.get("/api/options")
def get_options(column_name: str = "column_name"):
    # return all options for a column
    # if column_name is None, return all options for column_name
    
    if column_name in ["id", "abs_path", "album_art"]:
        #return empty list because these columns are either all unique or blob
        options = []

    #other colums:
    #name, bpm, length, kbps, genre, artist, album
    elif column_name == "column_name":
        #return all column names
        options = fcore.SongEntry(0, "", "", 0, 0, 0, "", "", "", "").__dict__.keys()
        options = list(options)
        
        print(options)
        
        #remove id, abs_path and album_art
        options.remove("id")
        options.remove("abs_path")
        options.remove("album_art")
        
        options = list(options)
    else:
        #return all options for column_name
        options = set()
        songs = db.get_all_songs()
        
        for song in songs:
            options.add(song.__dict__[column_name])
        
        options = list(options)
    
    return JSONResponse({"options": options})
    



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
