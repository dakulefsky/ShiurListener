"""Explicit, local profile backups. Audio files are never part of a backup."""
import copy
import datetime
import json
import math
import os
import pathlib
import re
import tempfile


FORMAT = 'shiur-player-backup'
MAX_BYTES = 32 * 1024 * 1024
RATES = (.5, .75, 1, 1.25, 1.5, 1.75, 2)
# These settings refer to this computer and already-running native windows.
DEVICE_SETTINGS = ('libraryRoot', 'globalShortcuts', 'floatingVisible', 'floatingCollapsed', 'mainDockCollapsed',
                   'floatingPosition', 'floatingSize', 'windowSize')


def _require(condition, message):
    if not condition:
        raise ValueError('Invalid player backup: ' + message)


def _number(value, maximum=1e8):
    return (type(value) in (int, float) and 0 <= value < maximum
            and math.isfinite(value))


def _ident(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value) is not None


def _ids(value):
    return (isinstance(value, list) and len(value) <= 100000
            and all(_ident(item) for item in value)
            and len(value) == len(set(value)))


def _text(value, maximum=160, empty=False):
    return isinstance(value, str) and (empty or bool(value.strip())) and len(value) <= maximum


def _validate(payload):
    _require(isinstance(payload, dict), 'expected a JSON object.')
    _require(payload.get('format') == FORMAT and type(payload.get('version')) is int
             and payload['version'] == 1, 'unsupported backup format or version.')
    state = payload.get('state')
    _require(isinstance(state, dict), 'saved profile is missing.')
    allowed = {'tracks', 'folders', 'bookmarks', 'currentId', 'queue', 'autoNext',
               'speed', 'volume', 'skipSeconds', 'language', 'libraryRoot', 'audioEnhancement', 'speechEnhancementEnabled', 'speechEnhancementStrength',
               'librarySort', 'librarySortDescending', 'floatingVisible', 'floatingCollapsed', 'mainDockCollapsed',
               'floatingPosition', 'floatingSize', 'windowSize', 'floatingTheme',
               'halfSpeedCycleMigration', 'miniOnMinimize', 'globalShortcuts', 'miniSpeedMiddle', 'miniSpeedCycleIndex'}
    _require(not (set(state) - allowed), 'this profile contains settings from a newer player.')
    tracks = state.get('tracks')
    _require(isinstance(tracks, dict) and len(tracks) <= 100000, 'recording positions are missing.')
    for ident, track in tracks.items():
        _require(_ident(ident) and isinstance(track, dict), 'invalid recording entry.')
        _require(not (set(track) - {'position', 'duration', 'completed', 'lastListenedAt', 'favorite', 'speed'}),
                 'invalid recording fields.')
        if 'speed' in track:
            _require(_number(track['speed']) and track['speed'] in RATES, 'invalid recording speed.')
        for key in ('position', 'duration'):
            if key in track:
                _require(_number(track[key]), 'invalid recording ' + key + '.')
        for key in ('completed', 'favorite'):
            if key in track:
                _require(type(track[key]) is bool, 'invalid recording ' + key + '.')
        if 'lastListenedAt' in track:
            _require(_number(track['lastListenedAt'], 1e30), 'invalid listening date.')
    folders = state.get('folders')
    _require(isinstance(folders, list) and len(folders) <= 10000, 'collections are missing.')
    folder_ids = set()
    for folder in folders:
        _require(isinstance(folder, dict) and set(folder) == {'id', 'name', 'trackIds'},
                 'invalid collection entry.')
        _require(_ident(folder['id']) and folder['id'] not in folder_ids
                 and folder['id'] not in ('all', 'continue', 'favorites', 'unplayed', 'finished'),
                 'invalid or duplicate collection identifier.')
        _require(_text(folder['name']) and _ids(folder['trackIds']), 'invalid collection name or recordings.')
        folder_ids.add(folder['id'])
    bookmarks = state.get('bookmarks', {})
    _require(isinstance(bookmarks, dict) and len(bookmarks) <= 100000, 'invalid bookmarks.')
    for ident, marks in bookmarks.items():
        _require(_ident(ident) and isinstance(marks, list) and len(marks) <= 10000, 'invalid bookmark list.')
        mark_ids = set()
        for mark in marks:
            _require(isinstance(mark, dict) and set(mark) == {'id', 'name', 'position'}, 'invalid bookmark.')
            _require(_ident(mark['id']) and mark['id'] not in mark_ids
                     and _text(mark['name'], empty=True) and _number(mark['position']), 'invalid bookmark values.')
            mark_ids.add(mark['id'])
    if 'currentId' in state:
        _require(state['currentId'] is None or _ident(state['currentId']), 'invalid current recording.')
    if 'queue' in state:
        _require(_ids(state['queue']), 'invalid play queue.')
    if 'speed' in state:
        _require(_number(state['speed']) and state['speed'] in RATES, 'invalid playback speed.')
    if 'volume' in state:
        _require(_number(state['volume']) and state['volume'] <= 1, 'invalid volume.')
    if 'skipSeconds' in state:
        _require(type(state['skipSeconds']) is int and state['skipSeconds'] in (10, 15, 60), 'invalid skip interval.')
    for key in ('autoNext', 'librarySortDescending', 'floatingVisible', 'floatingCollapsed', 'mainDockCollapsed', 'miniOnMinimize', 'globalShortcuts', 'speechEnhancementEnabled'):
        if key in state:
            _require(type(state[key]) is bool, 'invalid ' + key + '.')
    for key in ('floatingPosition', 'floatingSize', 'windowSize'):
        if key in state:
            value = state[key]
            minimum = -100000 if key == 'floatingPosition' else 1
            _require(isinstance(value, list) and len(value) == 2
                     and all(type(n) is int and minimum <= n <= 100000 for n in value), 'invalid window bounds.')
    if 'libraryRoot' in state:
        _require(_text(state['libraryRoot'], 32768), 'invalid library folder.')
    if 'librarySort' in state:
        _require(state['librarySort'] in ('name', 'resume', 'duration'), 'invalid library sort order.')
    if 'language' in state:
        _require(state['language'] in ('he', 'en'), 'invalid language.')
    if 'miniSpeedMiddle' in state:
        _require(_number(state['miniSpeedMiddle']) and state['miniSpeedMiddle'] in (.5, 1.5), 'invalid mini-player speed.')
    if 'miniSpeedCycleIndex' in state:
        value = state['miniSpeedCycleIndex']
        _require(value is None or (type(value) is int and 0 <= value < 4), 'invalid speed cycle.')
    if 'audioEnhancement' in state:
        audio = state['audioEnhancement']
        _require(isinstance(audio, dict) and set(audio) <= {'bass', 'body', 'clarity', 'treble'},
                 'invalid audio enhancement settings.')
        for name, value in audio.items():
            _require(type(value) in (int, float) and math.isfinite(value) and -6 <= value <= 6,
                     'audio enhancement values must be between -6 and +6 dB.')
    if 'speechEnhancementStrength' in state:
        value = state['speechEnhancementStrength']
        _require(type(value) is int and 10 <= value <= 60, 'speech suppression strength must be between 10 and 60.')
    if 'floatingTheme' in state:
        theme = state['floatingTheme']
        colors = ('primary', 'onPrimary', 'surface', 'onSurface', 'surfaceContainer')
        _require(isinstance(theme, dict) and not (set(theme) - set(colors) - {'fontFamily'}), 'invalid mini-player colors.')
        for key, value in theme.items():
            _require(_text(value, 100) if key == 'fontFamily' else
                     isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value), 'invalid mini-player theme.')
    return copy.deepcopy(state)


def _read(path):
    try:
        with pathlib.Path(path).open('rb') as stream:
            data = stream.read(MAX_BYTES + 1)
        _require(len(data) <= MAX_BYTES, 'file exceeds 32 MB.')
        return json.loads(data.decode('utf-8'))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError('Invalid player backup: the file is not readable JSON.') from error


def _write(path, state):
    path = pathlib.Path(path)
    data = json.dumps({'format': FORMAT, 'version': 1, 'state': state},
                      ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    _require(len(data) <= MAX_BYTES, 'profile exceeds 32 MB.')
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def export_profile(player, path):
    """Write a backup to a chosen JSON file, refusing unrelated existing files."""
    path = pathlib.Path(path).resolve()
    if path.suffix.lower() != '.json' or path == player.file.resolve():
        raise ValueError('Choose a separate .json file for your player backup.')
    if path.exists():
        try:
            _validate(_read(path))
        except (ValueError, OSError) as error:
            raise ValueError('That file is not a player backup. Choose a different filename.') from error
    with player.lock:
        player.capture()
        player.persist()
        state = copy.deepcopy(player.saved)
    _write(path, state)
    return path


def import_profile(player, path):
    """Restore a validated backup, keeping this library and a pre-restore backup.

    Returns the safety backup path. Playback remains stopped, with the restored
    current recording ready to resume. Existing files and audio folders stay put.
    """
    restored = _validate(_read(path))
    with player.lock:
        player.capture()
        player.persist()
        previous = copy.deepcopy(player.saved)
        safety = player.data_dir / ('state-before-restore-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
        _write(safety, previous)
        state = {'currentId': None, 'queue': [], 'autoNext': False, 'speed': 1,
                 'volume': 1, 'skipSeconds': 15, 'bookmarks': {}, 'language': 'en', **restored}
        for key in DEVICE_SETTINGS:
            state.pop(key, None)
            if key in previous:
                state[key] = previous[key]
        if player.root is not None:
            state['libraryRoot'] = str(player.root)
        state['language'] = 'en'
        state['queue'] = [ident for ident in state['queue'] if ident in player.paths]
        if state['currentId'] not in player.paths:
            state['currentId'] = None
        player.backend.stop()
        player.active = None
        player.pending = None
        player.seek_target = None
        player.was_playing = False
        player.sleep_deadline = None
        player.sleep_minutes = 0
        player.sleep_paused = False
        player.sleep_at_end = False
        if hasattr(player, 'clear_loop'):
            player.clear_loop()
        player.saved = state
        try:
            player.persist()
        except Exception:
            player.saved = previous
            raise
        player.previous_status = 'stopped'
        player.error = ''
        player.library_revision += 1
        return safety
