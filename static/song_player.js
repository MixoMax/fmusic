let song_data = "song_data_placeholder";
/*{
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
*/

let song_url = ""
let audio = null;
let shuffle = null;
let is_favorite = null;

function var_setup(song_data) {

    console.log("var_setup");

    song_url = "/api/song/" + song_data.id;
    audio = new Audio(song_url);

    audio.crossOrigin = "anonymous";
    audio.load();

    audio.addEventListener("timeupdate", update_progress_bar);

    shuffle = get_shuffle();

    is_favorite = false;

}

function onload_song() {
    console.log("onload_song");

    update_favorite_button();
    update_shuffle_button();

    //set <title> to song name

    let title = song_data.name + " - " + song_data.artist;
    document.title = title;

    document.getElementById("song-title").innerHTML = song_data.name + " - " + song_data.artist;
    

    //set src in <img id = "spectogram"> to /api/specogram/<song_id>
    update_spectogram();


    //Event Listeners and setIntervals
    audio.addEventListener("timeupdate", update_progress_bar);
    
    //clickable progress bar
    document.getElementById("progress-bar-container").addEventListener("click", function (e) {
        const container = this;
        const offsetX = e.clientX - container.getBoundingClientRect().left;
        const percentage = offsetX / container.clientWidth;
    
        skip_to_percentage(percentage);
    });

    document.addEventListener("keydown", handle_key_press);

    //play/pause button
    setInterval(update_play_pause_button, 100);

    setInterval(update_shuffle_button, 100);
    
    //call update_progress_bar once after 1ms
    setTimeout(update_progress_bar, 1);

}

function playSong() {
    //play or pause the song

    if (audio.paused) {
        audio.play();
    } else {
        audio.pause();
    }

    update_play_pause_button();
}

function update_spectogram() {
    //update the spectogram

    let url = "/api/spectogram/" + song_data.id;
    document.getElementById("spectogram").src = url;
}

function update_spectogram_bar() {
    let elem = document.getElementById("spectogram-bar");

    //bar that overlays the spectogram image
    //bar position x is based on audio.currentTime
    //width is constant

    let percentage = audio.currentTime / audio.duration;
    
    elem.style.left = percentage * 100 + "%";
}

function update_play_pause_button() {
    //update the play/pause button using the audio.paused property
    //use Pictogram

    const play_pause_button = document.getElementById("play-pause-button");

    if (audio.paused) {
        play_pause_button.innerHTML = "<span>&#9658;</span>" //play triangle
    } else {
        play_pause_button.innerHTML = "<span><b>||</b></span>"
    }
}

function skipBack() {
    audio.currentTime -= 10;
}

function skipForward() {
    audio.currentTime += 10;
}

function skip_to_percentage(percentage) {
    audio.currentTime = audio.duration * percentage;
}

async function get_max_song_id() {
    let url = "/api/get_num_songs";
    // -> {"num_songs": 10}

    try {
        let response = await fetch(url);
        let data = await response.json();

        return data.num_songs;
    } catch (error) {
        console.log(error);
    }
}

async function skip_to_next_song() {
    
    if (shuffle) {
        let max_song_id = await get_max_song_id();

        let max_id = parseInt(max_song_id); //NaN


        //choose a random id between 1 and max_song_id
        let next_song_id = Math.floor(Math.random() * max_id) + 1;

        let url = "/song/" + next_song_id;

        window.location.href = url;
    } else {
        //skip to the next song in the playlist
        let next_song_id = song_data.id + 1;
        let url = "/song/" + next_song_id;
        
        //href to url
        window.location.href = url;
    }


}

function skip_to_previous_song() {
    //skip to the previous song in the playlist
    let previous_song_id = song_data.id - 1;

    let url = "/song/" + previous_song_id;

    window.location.href = url;
}

function toggleShuffle() {
    //toggle shuffle
    let old_shuffle = get_shuffle();
    let new_shuffle = !old_shuffle;

    update_shuffle_button();
    save_shuffle(new_shuffle);
}

function update_shuffle_button() {
    //update the shuffle button using the shuffle variable
    const shuffle_button = document.getElementById("shuffle_button");

    shuffle = get_shuffle();

    if (shuffle) {
        shuffle_button.style.backgroundColor = "#3498db";
    } else {
        shuffle_button.style.backgroundColor = "#676767";
    }
}

function restart_song() {
    //restart the song
    audio.currentTime = 0;
}

async function check_if_favorite() {
    let url = "/api/favorites/is_favorite/" + song_data.id;

    try {
        let response = await fetch(url);
        let data = await response.json();

        return data.is_favorite;
    } catch (error) {
        console.log(error);
    }
}

async function toggle_favorite() {

    let url = ""
    if (is_favorite) {
        url = "/api/favorites/remove/" + song_data.id;
    } else {
        url = "/api/favorites/add/" + song_data.id;

        //little explosion animation when the favorite button is clicked
        favorite_button_explosion();
    }

    is_favorite = !is_favorite;

    try {
        let response = await fetch(url);
        let data = await response.json();

    } catch (error) {
        console.log(error);
    }

    update_favorite_button();

}

async function update_favorite_button() {

    is_favorite = await check_if_favorite();
    //update the favorite button using the is_favorite variable
    const favorite_button = document.getElementById("favorite_button");

    if (is_favorite) {
        //set text to filled heart
        favorite_button.innerHTML = "&#x2665;";

        //set text color to red
        favorite_button.style.color = "red";

        //set color to blue
        favorite_button.style.backgroundColor = "#3498db";

    } else {
        //set text to empty heart
        favorite_button.innerHTML = "&#x2661;";
        //set text color to white
        favorite_button.style.color = "white";

        //set color to gray
        favorite_button.style.backgroundColor = "#676767";
    }
}

async function favorite_button_explosion() {
    //little explosion animation when the favorite button is clicked
    const favorite_button = document.getElementById("favorite_button");

    //create 10 heart emojis
    //that move in random directions
    //and fade out
    let max_distance = 250;
    let num_hearts = 50;
    for (let i = 0; i < num_hearts; i++) {
        const heart = document.createElement("span");

        let heart_size = Math.random() * 20 + 10;
        let random_distance = Math.random() * max_distance;

        let offset_top = favorite_button.offsetTop - 25;

        heart.innerHTML = "&#x2665;";
        heart.style.position = "absolute";
        heart.style.left = favorite_button.offsetLeft + "px";
        heart.style.top = offset_top + "px";
        heart.style.color = "red";
        heart.style.transition = "all 1s ease-in-out";
        heart.style.fontSize = heart_size + "px";
        heart.style.opacity = "1";

        document.body.appendChild(heart);

        const randomX = Math.random() * random_distance * 2 - random_distance;
        const randomY = Math.random() * random_distance * 2 - random_distance;

        setTimeout(() => {
            heart.style.transform = `translate(${randomX}px, ${randomY}px) scale(0.5)`;
            heart.style.opacity = "0";
        }, 100);

        setTimeout(() => {
            document.body.removeChild(heart);
        }, 1100);
    }
}

function get_shuffle() {
    //get shuffle from local storage
    //if it doesn't exist, set it to true
    let shuffle = localStorage.getItem("shuffle");


    if (shuffle == null) {
        shuffle = true;
        localStorage.setItem("shuffle", shuffle);
    } else {
        shuffle = shuffle == "true";
    }


    return shuffle;
}

function save_shuffle(new_shuffle) {

    //save shuffle to local storage
    localStorage.setItem("shuffle", new_shuffle);
}

function handle_key_press(e) {

    if (e.code == "Space") {
        playSong();
    } else if (e.code == "ArrowLeft") {
        skipBack();
    } else if (e.code == "ArrowRight") {
        skipForward();
    } else if (e.code == "MediaTrackPrevious") {
        skip_to_previous_song();
    } else if (e.code == "MediaTrackNext") {
        skip_to_next_song();
    } else if (e.code == "KeyS") {
        toggleShuffle();
    } else if (e.code == "KeyR") {
        restart_song();
    }

}

function convert_ss_to_mmss(seconds) {
    //convert seconds to mm:ss
    let minutes = Math.floor(seconds / 60);
    let seconds_str = Math.floor(seconds % 60).toString();

    if (seconds_str.length == 1) {
        seconds_str = "0" + seconds_str;
    }

    //if minute or second is NaN, return "infinity"

    if (isNaN(minutes) || isNaN(seconds)) {
        return "infinity";
    }

    return minutes + ":" + seconds_str;
}

function update_progress_bar() {
    
    const progress_bar = document.getElementById("progress-bar");
    const progress = audio.currentTime / audio.duration;
    progress_bar.style.width = progress * 100 + "%";

    const time = document.getElementById("time");
    const current_time = Math.floor(audio.currentTime);
    const total_time = Math.floor(audio.duration);


    time.innerHTML = convert_ss_to_mmss(current_time) + " / " + convert_ss_to_mmss(total_time);

    update_spectogram_bar();
}