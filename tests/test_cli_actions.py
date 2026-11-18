import contextlib
import io
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import iheart.player as player_module
from iheart.__main__ import iHeart, iHeart_CLI, main


class ConfigStub:
    def __init__(self, datadir):
        self._datadir = datadir
        self.conffile = os.path.join(datadir, "iheartcli.ini")

    def get_datadir(self):
        return self._datadir

    def get_bool(self, key, default):
        return default

    def get_int(self, key, default):
        return default


class StationStub:
    name = "Morning / News"

    def __init__(self):
        self.recording_path = None

    def is_recording(self):
        return self.recording_path is not None

    def start_recording(self, path):
        self.recording_path = path
        return path

    def stop_recording(self):
        path = self.recording_path
        self.recording_path = None
        return path


class FailingStation(StationStub):
    def start_recording(self, path):
        raise RuntimeError("stream unavailable")


class MediaStub:
    def __init__(self):
        self.options = []

    def add_option(self, option):
        self.options.append(option)


class RecorderStub:
    def __init__(self):
        self.media = None
        self.played = False
        self.stopped = False
        self.released = False

    def set_media(self, media):
        self.media = media

    def play(self):
        self.played = True

    def get_state(self):
        return player_module.vlc.State.Playing

    def stop(self):
        self.stopped = True

    def release(self):
        self.released = True


class InstanceStub:
    def __init__(self):
        self.media = MediaStub()
        self.recorder = RecorderStub()

    def media_new(self, mrl):
        return self.media

    def media_player_new(self):
        return self.recorder


class CliActionsTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cli = iHeart_CLI(ConfigStub(self.tempdir.name))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_record_toggle_starts_and_stops_recording(self):
        station = StationStub()
        self.cli.station = station

        started = self.cli.toggle_recording()
        self.assertEqual(started, station.recording_path)
        self.assertTrue(started.startswith(os.path.join(self.tempdir.name, "recordings")))
        self.assertIn("Morning_News", started)
        self.assertTrue(started.endswith(".mp3"))

        stopped = self.cli.toggle_recording()
        self.assertEqual(stopped, started)
        self.assertIsNone(station.recording_path)

    def test_record_toggle_reports_failure(self):
        self.cli.station = FailingStation()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = self.cli.toggle_recording()

        self.assertIsNone(result)
        self.assertIn("Recording failed", output.getvalue())

    def test_player_recording_configures_and_releases_vlc_output(self):
        instance = InstanceStub()
        fake_vlc = SimpleNamespace(
            State=SimpleNamespace(Playing="playing", Ended="ended", Stopped="stopped")
        )
        with tempfile.TemporaryDirectory() as directory, patch.object(
            player_module, "vlc", fake_vlc
        ):
            player = player_module.VLCPlayer("https://example.test/live")
            player.inst = instance
            player.plr = object()
            path = player.start_recording(os.path.join(directory, "segment.mp3"))

            self.assertTrue(instance.recorder.played)
            self.assertIn(":sout=#transcode", instance.media.options[0])
            self.assertEqual(player.stop_recording(), path)
            self.assertTrue(instance.recorder.stopped)
            self.assertTrue(instance.recorder.released)

    def test_search_rejects_response_without_requested_category(self):
        radio = iHeart("unused.uuid")
        with patch("iheart.__main__.iheart_client.ilogin", return_value={"profileId": "1"}), \
             patch("iheart.__main__.iheart_client.isearch", return_value={"results": {}}):
            with self.assertRaises(ValueError):
                radio.search("missing", category=iHeart.TRACKS)

    def test_empty_search_result_does_not_prompt_for_selection(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = self.cli.list_current_stations(getter=lambda start: [])

        self.assertIsNone(result)
        self.assertIn("Nothing found", output.getvalue())

    def test_playlist_name_with_path_separator_is_rejected(self):
        station = StationStub()
        self.cli.station = station
        with patch.object(self.cli.store, "add_to_playlist") as add_to_playlist, \
             patch("builtins.input", side_effect=["0", "../unsafe"]):
            self.cli.add_to_playlist()

        add_to_playlist.assert_not_called()

    def test_shuffle_requires_playlist(self):
        with patch.object(sys, "argv", ["iheart", "--shuffle"]):
            with self.assertRaises(SystemExit) as raised:
                main()

        self.assertEqual(raised.exception.code, 2)
