"""Profile restore must be recoverable and must never replace audio files."""
import copy
import json
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'app'))
from engine import Player
from profile_backup import export_profile, import_profile
import test_player


class Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_player.Tests()
        self.fixture.setUp()
        self.player = self.fixture.player
        self.library = self.fixture.library
        self.backend = self.fixture.backend
        self.root = self.fixture.root
        self.ids = [track['id'] for track in self.player.tracks]
        self.backup = self.root / 'listening-backup.json'

    def tearDown(self):
        self.fixture.tearDown()

    def write_payload(self, state):
        self.backup.write_text(json.dumps({'format': 'shiur-player-backup', 'version': 1, 'state': state}))

    def test_roundtrip_keeps_multiple_positions_favorites_collections_and_bookmarks(self):
        self.library.play()
        self.player.tick()
        self.backend.position = 42.987
        self.library.mark('Review this point')
        self.player.saved['tracks'][self.ids[1]] = {'position': 19.375, 'duration': 120, 'favorite': True}
        self.library.assign_many(self.ids, 'My series')
        self.player.saved['speed'] = 1.5
        original_audio = {path.name: path.read_bytes() for path in self.fixture.audio.iterdir()}
        export_profile(self.player, self.backup)
        self.backend.position = 70.125
        self.player.saved['tracks'][self.ids[1]]['position'] = 81
        self.player.saved['folders'] = []
        self.player.saved['bookmarks'] = {}
        safety = import_profile(self.player, self.backup)
        self.assertEqual(self.player.snapshot()['position'], 42.987)
        self.assertEqual(self.player.saved['tracks'][self.ids[1]]['position'], 19.375)
        self.assertTrue(self.player.saved['tracks'][self.ids[1]]['favorite'])
        self.assertEqual(self.player.saved['folders'][0]['name'], 'My series')
        self.assertEqual(self.library.bookmarks()[0]['name'], 'Review this point')
        self.assertEqual(self.player.saved['speed'], 1.5)
        self.assertEqual(self.backend.status, 'stopped')
        self.assertIsNone(self.player.active)
        self.assertIsNone(self.player.pending)
        self.assertEqual(json.loads(safety.read_text())['state']['tracks'][self.ids[0]]['position'], 70.125)
        self.assertEqual(original_audio, {path.name: path.read_bytes() for path in self.fixture.audio.iterdir()})
        reopened = Player(None, self.player.data_dir, test_player.Audio())
        self.assertEqual(reopened.saved['tracks'][self.ids[1]]['position'], 19.375)

    def test_restore_preserves_language_from_backup(self):
        state = copy.deepcopy(self.player.saved)
        state['language'] = 'he'
        self.write_payload(state)
        import_profile(self.player, self.backup)
        self.assertEqual(self.player.saved['language'], 'he')

    def test_restore_keeps_current_library_and_native_window_preferences(self):
        state = copy.deepcopy(self.player.saved)
        state.update(libraryRoot='Z:/different-machine/audio', globalShortcuts=True,
                     floatingVisible=True, floatingPosition=[9, 10], windowSize=[1500, 900])
        self.player.saved.update(globalShortcuts=False, floatingVisible=False, windowSize=[1000, 700])
        self.write_payload(state)
        import_profile(self.player, self.backup)
        self.assertEqual(self.player.root, self.fixture.audio)
        self.assertEqual(self.player.saved['libraryRoot'], str(self.fixture.audio))
        self.assertFalse(self.player.saved['globalShortcuts'])
        self.assertFalse(self.player.saved['floatingVisible'])
        self.assertNotIn('floatingPosition', self.player.saved)
        self.assertEqual(self.player.saved['windowSize'], [1000, 700])

    def test_bad_known_fields_never_mutate_live_profile_or_stop_audio(self):
        self.library.play()
        self.player.tick()
        before = copy.deepcopy(self.player.saved)
        disk_before = self.player.file.read_bytes()
        invalid = [
            {'tracks': []}, {'folders': {}}, {'speed': True}, {'volume': float('nan')},
            {'currentId': []}, {'queue': ['missing', 'missing']}, {'windowSize': [True, 700]},
            {'floatingTheme': {'primary': 'purple'}}, {'globalShortcuts': 'yes'}, {'speechEnhancementEnabled': 'yes'}, {'speechEnhancementStrength': 5},
            {'tracks': {self.ids[0]: {'position': -1}}},
            {'tracks': {self.ids[0]: {'duration': float('inf')}}},
            {'tracks': {self.ids[0]: {'position': 10 ** 400}}},
            {'tracks': {self.ids[0]: {'id': 'spoofed'}}},
            {'bookmarks': {self.ids[0]: [{'id': 'bookmark', 'position': '1:30', 'name': 'Point'}]}},
            {'folders': [{'id': 'all', 'name': 'Hidden view', 'trackIds': []}]},
            {'folders': [{'id': 'abc', 'name': 'Series', 'trackIds': {}}]},
        ]
        for change in invalid:
            with self.subTest(change=change):
                self.write_payload({**before, **change})
                with self.assertRaises(ValueError):
                    import_profile(self.player, self.backup)
                self.assertEqual(self.player.saved, before)
                self.assertEqual(self.player.file.read_bytes(), disk_before)
                self.assertEqual(self.backend.status, 'playing')
        self.assertEqual(list(self.player.data_dir.glob('state-before-restore-*.json')), [])

    def test_unavailable_tracks_remain_in_progress_but_are_removed_from_queue(self):
        state = copy.deepcopy(self.player.saved)
        state.update(currentId='missing', queue=[self.ids[0], 'missing'],
                     tracks={'missing': {'position': 65.432}})
        self.write_payload(state)
        import_profile(self.player, self.backup)
        self.assertIsNone(self.player.saved['currentId'])
        self.assertEqual(self.player.saved['queue'], [self.ids[0]])
        self.assertEqual(self.player.saved['tracks']['missing']['position'], 65.432)

    def test_export_cannot_overwrite_audio_state_or_unrelated_json(self):
        unrelated = self.root / 'configuration.json'
        unrelated.write_text('{"activeVersion":"0.6.0"}')
        audio = self.fixture.audio / '01.wav'
        for path in [audio, self.player.file, unrelated]:
            with self.subTest(path=path):
                before = path.read_bytes()
                with self.assertRaises(ValueError):
                    export_profile(self.player, path)
                self.assertEqual(path.read_bytes(), before)

    def test_export_can_replace_an_existing_valid_backup(self):
        export_profile(self.player, self.backup)
        self.player.saved['tracks'][self.ids[0]] = {'position': 12.345}
        export_profile(self.player, self.backup)
        self.assertEqual(json.loads(self.backup.read_text())['state']['tracks'][self.ids[0]]['position'], 12.345)

    def test_restore_persist_failure_keeps_previous_profile_and_safety_copy(self):
        self.library.play()
        self.player.tick()
        active_before = self.player.active
        export_profile(self.player, self.backup)
        self.player.saved['tracks'][self.ids[0]] = {'position': 55.5}
        self.backend.position = 55.5
        self.player.capture()
        self.player.persist()
        before = copy.deepcopy(self.player.saved)
        actual_persist = self.player.persist
        writes = 0
        def persist():
            nonlocal writes
            writes += 1
            if writes == 2:
                raise OSError('Disk full')
            actual_persist()
        with mock.patch.object(self.player, 'persist', side_effect=persist):
            with self.assertRaises(OSError):
                import_profile(self.player, self.backup)
        self.assertEqual(self.player.saved, before)
        self.assertEqual(json.loads(self.player.file.read_text()), before)
        self.assertEqual(self.player.active, active_before)
        self.assertEqual(self.backend.status, 'playing')
        self.assertEqual(len(list(self.player.data_dir.glob('state-before-restore-*.json'))), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
