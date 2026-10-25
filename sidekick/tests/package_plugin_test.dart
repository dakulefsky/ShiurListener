import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:otzaria/plugins/services/plugin_packager_cli.dart';

void main() {
  test('companion comparison installs separately and packages', () async {
    final root = Platform.environment['SIDEKICK_ROOT'] ?? '../shiur-player-companion-compare';
    final manifest = jsonDecode(
      File('$root/plugin/manifest.json').readAsStringSync(),
    ) as Map;
    expect(manifest['id'], 'org.shiurplayer.companion');
    expect(manifest['permissions'], contains('network.localhost'));
    expect(manifest['permissions'], isNot(contains('app.open_url')));
    expect((manifest['network'] as Map)['allowlist'], [
      'http://127.0.0.1:18473',
    ]);
    final code = await PluginPackagerCli.run([
      '$root/plugin',
      '--force',
      '--output',
      '$root/sidekick-1.1.0.otzplugin',
    ]);
    expect(code, PluginPackagerCliExitCode.success);
  });
}
