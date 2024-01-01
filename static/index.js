

var search_query = {
    limit: 10,
    mode: "AND",
    bpm: [],
    length: [],
    kbps: [],
    genre: [],
    artist: [],
    album: [],
    name: []
}
//{
//    limit: int,
//    mode: "AND" | "OR",
//    bpm: int | list(int),
//    length: int | list(int),
//    kbps: int | list(int),
//    genre: str | list(str),
//    artist: str | list(str),
//    album: str | list(str),
//    name: str | list(str)
//}

//for bpm, length, kbps:
//if int: exact match
//if list(int) with length 2: bpm[0] <= x <= bpm[1]
//if list(int) with length >2: bpm in list



var current_songs = {};
var currently_playing_song_id = null;
var audio;


//select2 for select id = SearchCategory
$(document).ready(function () {
    $("#SearchCategory").select2({
        placeholder: "Select a category",
        allowClear: true
    });
}
);

//select2 for select id = SearchValues

$(document).ready(function () {
    $("#SearchValues").select2({
        placeholder: "Value",
        allowClear: true
    });
}
);

function updateSearchValues() {
    //get new search category
    //get all options within that category from backend: /api/get_options?column_name=SearchCategory
    //SearchCategory can be: name, bpm, length, kbps, genre, artist, album

    let searchCategory = document.getElementById("SearchCategory").value;

    console.log("Search category:", searchCategory);

    let available_options = ["name", "bpm", "length", "kbps", "genre", "artist", "album"];

    if (!available_options.includes(searchCategory)) {
        console.error("Invalid search category:", searchCategory);
        return;
    }

    var url = "/api/options?column_name=" + searchCategory;

    data = fetch(url).then(response => response.json()).then(data => {
        //->{"options": list(options)}
        return data.options;
    });

    //update options in SearchValues

    data.then(options => {
        let select = document.getElementById("SearchValues");

        //remove all options
        select.innerHTML = "";

        //add new options
        options.forEach(option => {

            let option_element = document.createElement("option");
            option_element.value = option;
            option_element.innerHTML = option;
            select.appendChild(option_element);
        });
    });
}

function get_search_categories() {
    var url = "/api/options?column_name=column_name";


    data = fetch(url).then(response => response.json()).then(data => {
        //->{"options": list(options)}
        return data.options;
    });

    //return list of str
    return data;
}

function updateSearchCategories() {
    let searchCategories = get_search_categories();

    searchCategories.then(categories => {
        let select = document.getElementById("SearchCategory");

        //remove all options
        select.innerHTML = "";

        //add new options
        categories.forEach(category => {

            let option_element = document.createElement("option");
            option_element.value = category;
            option_element.innerHTML = category;
            select.appendChild(option_element);
        });
    });
}

function addConstraint() {
    //add constraint to list
    
    let searchCategory = document.getElementById("SearchCategory").value;
    let value = document.getElementById("SearchValues").value;


    if (searchCategory == null || value == null) {
        console.error("Invalid search category or value:", searchCategory, value);
        return;
    }

    //append to search query[searchCategory]
    search_query[searchCategory].push(value);
}


function search() {
    var url = "/api/search_new";

    let request = new Request(url, {
        method: "POST",
        body: JSON.stringify(search_query),
        headers: {
            "Content-Type": "application/json"
        }
    });

    data = fetch(request).then(response => response.json()).then(data => {
        return data
    });

    return data.then(data => {
        console.log(data);
        return data;
    });
}

function append_song(song) {
    //@param song: {"name": str, "artist": str, "album": str, "genre": str, "length": int, "kbps": int, "bpm": int, "path": str}

    let div = document.getElementById("SearchResults");


    let song_div = document.createElement("div");
    song_div.className = "SongListEntry";

    let song_name = document.createElement("p");
    song_name.className = "Data";
    song_name.innerHTML = song.name;

    let song_artist = document.createElement("p");
    song_artist.className = "Data";
    song_artist.innerHTML = song.artist;

    let song_album = document.createElement("p");
    song_album.className = "Data";
    song_album.innerHTML = song.album;

    let song_genre = document.createElement("p");
    song_genre.className = "Data";
    song_genre.innerHTML = song.genre;

    let song_length = document.createElement("p");
    song_length.className = "Data";
    song_length.innerHTML = song.length;

    let song_kbps = document.createElement("p");
    song_kbps.className = "Data";
    song_kbps.innerHTML = song.kbps;

    let song_bpm = document.createElement("p");
    song_bpm.className = "Data";
    song_bpm.innerHTML = song.bpm;

    song_div.appendChild(song_name);
    song_div.appendChild(song_artist);
    song_div.appendChild(song_album);
    song_div.appendChild(song_genre);
    song_div.appendChild(song_length);
    song_div.appendChild(song_kbps);
    song_div.appendChild(song_bpm);

    div.appendChild(song_div);
}

async function search_and_append() {
    let data = await search();

    let div = document.getElementById("SearchResults");
    div.innerHTML = "";

    data.forEach(song => {
        append_song(song);
    });

    current_songs = data;
}

function handleKeyPress(e) {
    var key = e.keyCode || e.which;

    console.log("Key pressed:", key);

    if (key == 13) {
        //enter pressed
        
        //if focus is on #SearchBar -> search()

        //if focus is on #SearchValues -> addConstraint()

        //if focus is on #SearchCategory -> updateSearchValues()

        search_bar = document.getElementById("SearchBar");
        search_values = document.getElementById("SearchValues");
        search_category = document.getElementById("SearchCategory");

        if (document.activeElement == search_bar) {
            search();
        } else if (document.activeElement == search_values) {
            addConstraint();
        } else if (document.activeElement == search_category) {
            updateSearchValues();
        }
    }
}


function play_song(song_idx) {
    //song_idx: index of song in current_songs
    let song_id = current_songs[song_idx].id;

    let url = "/api/song/" + song_id;

    if (currently_playing_song_id == song_id) {
        //toggle play/pause
        if (audio.paused) {
            audio.play();
        } else {
            audio.pause();
        }
    } else {
        //play new song
        audio = new Audio(url);
        audio.play();
        currently_playing_song_id = song_id;
    }
}







function onload() {
    updateSearchCategories();
    updateSearchValues();
    
}

document.addEventListener("DOMContentLoaded", onload);
document.addEventListener("keypress", handleKeyPress);