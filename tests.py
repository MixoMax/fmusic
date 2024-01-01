import fmusic_core as fcore

import os
from termcolor import colored


#(id, name, abs_path, bpm, length (s), kbps, genre, artist, album, album_art)
songs = [
    (1, "Beat it", "/path/to/beatit.mp3", 120, 180, 320, "Rock", "Michael Jackson", "Thriller", b""),
    (2, "Godzilla ft. Juice WRLD", "/path/to/godzilla.mp3", 120, 180, 320, "Rap", "Eminem", "Music to be murdered by", b""),
    (3, "Bohemian Rhapsody", "/path/to/BohemianRhapsody", 80, 354, 320, "Rock", "Queen", "A Night at the Opera", b""),
    (4, "Shape of You", "/path/to/ShapeOfYou", 95, 234, 320, "Pop", "Ed Sheeran", "÷", b""),
    (5, "Thriller", "/path/to/Thriller", 118, 357, 320, "Pop", "Michael Jackson", "Thriller", b"")
]

songs = [
    fcore.SongEntry(id, name, abs_path, bpm, length, kbps, genre, artist, album, album_art)
    for id, name, abs_path, bpm, length, kbps, genre, artist, album, album_art in songs
]

test_song = (6, "Hotel California", "/path/to/HotelCalifornia", 75, 390, 320, "Rock", "Eagles", "Hotel California", b"")
test_song = fcore.SongEntry(*test_song)




if os.path.exists("test.db"):
    os.remove("test.db")

db = fcore.DataBase()
db.change_db("test.db")


#add songs
for song in songs:
    db.add_song(song)




# test get_song_by_id

current_test = "get_song_by_id"
all_passed = True

test_pairs = [ #id to test, expected result
    (1, songs[0]),
    (2, songs[1]),
    (3, songs[2]),
    (4, songs[3]),
    (5, songs[4]),
    (6, None),
    (-1, songs[4]),
    (-2, songs[3]),
    (-3, songs[2]),
    (-4, songs[1]),
    (-5, songs[0]),
    (-6, None)
]

for id, expected in test_pairs:
    result = db.get_song_by_id(id)
    if result != expected:
        print(colored(f"Test failed for id {id}", "red"))
        print(colored(f"Expected: {expected}", "red"))
        print(colored(f"Got: {result}", "red"))
        all_passed = False

if all_passed:
    print(colored(f"All tests passed for {current_test}", "green"))
else:
    print(colored(f"Some tests failed for {current_test}", "red"))



