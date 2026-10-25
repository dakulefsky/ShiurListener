import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:otzaria/plugins/services/plugin_packager_cli.dart';

void main() {
  test('visible player packages without a hidden background engine', () async {
    final root =
        Platform.environment['SHIUR_PLUGIN_ROOT'] ?? '../shiur-player-direct';
    final manifest = jsonDecode(
      File('$root/plugin/manifest.json').readAsStringSync(),
    ) as Map;
    expect(manifest['name'], 'נגן שיעורים');
    expect(manifest['id'], 'org.shiurplayer.local');
    expect((manifest['contributes'] as Map)['toolTab']['title'], 'נגן שיעורים');
    final permissions = (manifest['permissions'] as List).cast<String>();
    expect(
      permissions.any(
        (p) =>
            p.startsWith('audio.') ||
            p.startsWith('network.') ||
            p == 'app.open_url' ||
            p == 'app.run_on_startup' ||
            p == 'app.background_keep_alive',
      ),
      isFalse,
    );
    expect((manifest['contributes'] as Map).containsKey('background'), isFalse);
    expect(File('$root/plugin/background.html').existsSync(), isFalse);
    final code = await PluginPackagerCli.run([
      '$root/plugin',
      '--force',
      '--output',
      '$root/shiur-player-1.4.4.otzplugin',
    ]);
    expect(code, PluginPackagerCliExitCode.success);
    expect(File('$root/shiur-player-1.4.4.otzplugin').existsSync(), isTrue);
  });
}
