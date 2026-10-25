# Store upload review — נגן שיעורים 1.4.4

Reviewed on October 25, 2026 against the official SDK documentation, official validator and store upload code. This review concerns the Otzaria plugin, not the standalone Windows app.

## Manifest requirements

Sources: [SDK manifest documentation](https://github.com/Otzaria/otzaria/blob/dev/docs/plugin-sdk/README.md#קובץ-ה-manifest), [store upload handler](https://github.com/Otzaria/Otzaria_Website/blob/master/src/app/api/plugins/upload/route.js), [store text limits](https://github.com/Otzaria/Otzaria_Website/blob/master/src/lib/pluginSubmission.js), and [store stability/version policy](https://github.com/Otzaria/Otzaria_Website/blob/master/src/lib/pluginStatus.js).

| Field | Requirement | Packaged value |
|---|---|---|
| `schemaVersion` | Basic manifest requirement; must be 1 | `1` |
| `id` | Unique, stable plugin identifier | `org.shiurplayer.local` |
| `name` | Required; at most 14 characters | `נגן שיעורים` (11 characters) |
| `author` | Required for store upload; at most 100 characters | `DanTheMAn` |
| `description` | Required for store upload; at most 150 characters | Present, 73 characters |
| `version` | Required; `X.Y.Z`, with optional build metadata | `1.4.4` |
| `entrypoint` | Required; existing local entry file | `index.html` |
| `minAppVersion` | Required; must cover the APIs/permissions used and be at least the store floor, currently 0.9.89 | `0.9.98`, checked against the current SDK spec |
| `sdkVersion` | Basic manifest requirement | `1.x` |
| `contributes.toolTab.title` | If provided, must equal `name` | `נגן שיעורים` |
| `homepage` | Optional, recommended; must be HTTP(S) if supplied | Project's plugin directory on GitHub |
| `stability` | Optional, defaults to `stable`; valid values are `stable`, `beta`, `experimental` | Explicitly `experimental`, since an installed Otzaria app remains untested |
| `icon`, `maxAppVersion` | Optional | Omitted; the tab uses its declared headphones icon |

Network access remains disabled. Permissions remain `fs.user_files.read`, `app.startup_contributions`, and `reader.toolbar`. The ID and storage keys are unchanged, so this remains an update to the existing plugin.

The original pre-1.4.3 manifest omitted the store-required `author`. Version 1.4.3 already corrected that and passed validation. Version 1.4.4 adds the recommended homepage and makes stability explicit; neither field should be misrepresented as mandatory.

## What was validated

The official [Otzaria validator](https://github.com/Otzaria/otzaria-plugin-validator) at commit `64ee7c7806a03fcba16c111a7b6c3185e4d92804` (1.19.1) built the `.otzplugin`. Both the source directory and final archive were validated with the current `Otzaria/otzaria@dev` SDK spec and compatibility target `0.9.98`: **zero errors, zero warnings, zero design findings**. The source and ZIP metadata match. Playback source is unchanged except for the displayed version.

The local metadata preflight covers the store-only mandatory fields and text limits. The repository's validation workflow runs that preflight and the official validator with warnings treated as failures and `publish: false`. It has no store credentials and does not grant consent or submit a listing.

To check locally:

```sh
node player/build/check_store_manifest.cjs
npx --yes github:Otzaria/otzaria-plugin-validator#v1 player/plugin --fail-on-warnings --app-version 0.9.98 --publish false
```

These are developer checks; installed-plugin users need no Node/Python installation.

## First store upload — outside the manifest

The store separately requires an account/login, a long description, at least one screenshot (at most 10), and the publisher's explicit consent to receive user bug reports at the account email. A new listing also waits for administrator approval. These are upload-form requirements, not extra manifest fields. They cannot be satisfied by inventing fields such as `reportsConsent` inside `manifest.json`.

Use [this screenshot](../previews/shiur-player-plugin-1.4.4.png) if suitable. It is a capture of the actual plugin interface in Chromium with sample recordings and a simulated host bridge, not a capture from an installed Otzaria desktop app.

Suggested long description:

> נגן שיעורים לקובצי שמע מקומיים בתוך אוצריא. הנגן שומר מיקום האזנה נפרד לכל שיעור, ומציע תיקיות אישיות, חיפוש, סימניות, שינוי מהירות, דילוגים של 10 שניות, 15 שניות או דקה, טיימר שינה ומעבר אוטומטי לשיעור הבא. השיעורים נשארים במכשיר ואינם מועלים לרשת. ניתן להציג את הנגן לצד ספר פתוח. בגרסת אוצריא הנוכחית יש להשאיר את חלונית הנגן גלויה; מעבר לכרטיסייה שמסתירה אותה או מזעור אוצריא עשויים להשהות את השמע. אין צורך בתוכנה נלווית. הגרסה ניסיונית.

No listing was submitted. Passing local validation does not constitute store approval or verify physical audio output in an installed app.
