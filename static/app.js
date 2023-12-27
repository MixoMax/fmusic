
// fmusic: an open source music player
// Backend is written in FastAPI
// Path: static/app.js
// Author: MixoMax (https://Github.com/MixoMax)


// Apis:
// GET /api/song/<id>
// GET /api/song/<id>/info -> {id, name, abs_path, bpm, length, kbps, genre, artist, album, album_art}
// POST /api/song/upload <- {"file": binary of an mp3 file}

// SEARCH:
// GET /api/search?params={"mode": ["AND", "OR"], "limit": int, "bpm": int or (int, int), "length": int or (int, int), "kbps": int or (int, int), "genre": str, "artist": str, "album":: str, "name": str}
// GET /api/full_search?q=str

// PLAYLISTS:
// id = 0 is favorites
// GET /api/playlist/<id> -> {id, name, songs: [{id, name, abs_path, bpm, length, kbps, genre, artist, album, album_art}]}
// GET /api/playlist/<id>/art -> img file
// POST /api/playlist/<id>/add/<song_id>
// POST /api/playlist/create?name=<name>
// DELETE /api/playlist/{playlist_id}/delete
// DELETE /api/playlist/{playlist_id}/remove/{song_id}

// OTHER:
// GET /api/num_songs -> {num_songs: int}
// GET /api/get_options?column_name=<column_name> -> {options: [str]}
// GET /api/get_option_frequency?column_name=<column_name> -> {option:  str : frequency: int}
// column_name = bpm, length, kbps, genre, artist, album


import React from 'react';
import axios from 'axios';
import ReactDOM from 'react-dom';

class App extends React.Component {
  state = {
    currentSong: null,
    songInfo: null,
    playlist: [],
  };

  componentDidMount() {
    this.loadPlaylist(0); // Load favorites by default
  }

  // Function to load a song's info
  loadSongInfo = async (songId) => {
    try {
      const response = await axios.get(`/api/song/${songId}/info`);
      this.setState({ currentSong: songId, songInfo: response.data });
    } catch (error) {
      console.error('Error fetching song info:', error);
    }
  };

  // Function to load a playlist's songs
  loadPlaylist = async (playlistId) => {
    try {
      const response = await axios.get(`/api/playlist/${playlistId}`);
      this.setState({ playlist: response.data.songs });
    } catch (error) {
      console.error('Error fetching playlist:', error);
    }
  };

  render() {
    const { currentSong, songInfo, playlist } = this.state;
    return (
      <div>
        <h1>My Music Player</h1>
        <MusicPlayer songId={currentSong} songInfo={songInfo} />
        {/* You will also need to add components for searching, playlists, etc. */}
      </div>
    );
  }
}

class MusicPlayer extends React.Component {
    audioRef = React.createRef();
  
    componentDidUpdate(prevProps) {
      // Play the new song when the songId changes
      if (this.props.songId !== prevProps.songId && this.audioRef.current) {
        this.audioRef.current.load();
        this.audioRef.current.play();
      }
    }
  
    render() {
      const { songId, songInfo } = this.props;
      return (
        <div>
          {songInfo && (
            <>
              <h2>Now Playing: {songInfo.name}</h2>
              <audio ref={this.audioRef} controls>
                <source src={`/api/song/${songId}`} type="audio/mpeg" />
                Your browser does not support the audio element.
              </audio>
            </>
          )}
        </div>
      );
    }
  }


//html:
/*
<head>
<script src="https://unpkg.com/axios/dist/axios.min.js"></script>
<script src="https://unpkg.com/react@17/umd/react.development.js"></script>
<script src="https://unpkg.com/react-dom@17/umd/react-dom.development.js"></script>
<script src="https://unpkg.com/babel-standalone@6/babel.min.js"></script>

</head>

<body>
<div id="root"></div>
<script type="text/babel" src="/static/app.js"></script>
</body>
*/
