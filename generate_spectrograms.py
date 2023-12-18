from main import DataBase, SongEntry

import librosa
import numpy as np
import matplotlib.pyplot as plt
import PIL.Image as Image
import io
import os
import time


def calculate_spectogram(song:SongEntry):
    img_path = f"./temp/{song.id}.png"
    
    if os.path.exists(img_path):
        return
    
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

    

db = DataBase()

upper_limit = db.get_num_entries()
songs_left = upper_limit

for i in range(1, upper_limit+1):
    t_start = time.time()
    song = db.get_song_by_id(i)
    try:
        calculate_spectogram(song)
    except: #noqa
        print(f"Error with {song.id}")
        songs_left -= 1
        continue
    songs_left -= 1
    t_end = time.time()
    t_delta = t_end - t_start
    time_left = (t_delta * songs_left) / 60
    print(f"Done {i}/{upper_limit} ({time_left:.2f} minutes left)", end="\r")