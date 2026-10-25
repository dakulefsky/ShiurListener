import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:otzaria/plugins/services/plugin_file_server.dart';

void main() {
  test('Inside plays files served by the real Otzaria file server', () async {
    final root =
        Platform.environment['SHIUR_PLUGIN_ROOT'] ?? '../shiur-player-direct';
    final fixture = Directory.systemTemp.createTempSync('inside-media-');
    final server = PluginFileServer();
    try {
      final audio = File('${fixture.path}/recording.wav');
      final created = await Process.run('ffmpeg', [
        '-v',
        'error',
        '-f',
        'lavfi',
        '-i',
        'sine=frequency=220:sample_rate=8000',
        '-t',
        '120',
        '-ac',
        '1',
        audio.path,
      ]);
      expect(created.exitCode, 0, reason: '${created.stderr}');
      final registration = await server.register(
        pluginId: 'org.shiurplayer.local',
        canonicalPath: audio.path,
      );
      final result = await Process.run(
        'python',
        ['$root/tests/test_host_bridge.py'],
        environment: {'INSIDE_REAL_MEDIA_URL': registration.url},
      );
      print(result.stdout);
      expect(result.exitCode, 0, reason: '${result.stderr}');
    } finally {
      await server.close();
      fixture.deleteSync(recursive: true);
    }
  }, timeout: const Timeout(Duration(minutes: 2)));
}
