# Speech-priority two-check rerun

The model and exactly-two-check schedule were retained. Only decision aggregation changed: one strong speech sample (Speech score >=0.8) can pass unless both samples indicate music/singing. Two moderate speech samples (>=0.5 each) with no music hit also pass. Everything else remains uncertain.

This addresses the observed failure where one pause or weak excerpt caused a speech file to be withheld. The nine previously uncertain speech examples all had a clear speech excerpt; one also had a music-like excerpt.

| Source group | Before: provisional speech / music / uncertain | After: provisional speech / music / uncertain |
| --- | --- | --- |
| 64 speech clips | 55 / 0 / 9 | 64 / 0 / 0 |
| 64 music clips | 0 / 54 / 10 | 0 / 54 / 10 |
| Full Freifeld shiur | 1 / 0 / 0 | 1 / 0 / 0 |
| Five constructed music/speech examples | 3 / 1 / 1 | 4 / 1 / 0 |
| Silence and white noise | 0 / 0 / 2 | 0 / 0 / 2 |

The additional allowed mixed example is `spoken_intro_then_music.wav`. The user explicitly accepted the speech/music-mixture tradeoff in favor of avoiding rejected speech. Ten music examples remain uncertain; uncertainty is not converted wholesale into permission.

All 136 file fixtures were actually rescanned. Exactly two decoded excerpts and predictions per successful file, no follow-up checks. Eleven unit tests pass, including strong speech with a pause, strong speech plus one music candidate, both samples indicating music, silence, invalid scores and check count. No plugin/package/channel update was made.

Full per-file outputs, source hashes, check times, scores and reasons are in `speech-priority-file-results.json`. Original outcomes remain in `file-test-results.json` for comparison.

These were the same previously inspected sources. The threshold was selected after examining their errors, so this is not an independent held-out accuracy test or a guarantee that every future speech file will pass. Short sources were repeated into five-minute fixtures; only one actual full shiur was tested. Hebrew/Yiddish coverage remains unvalidated. Music between the two brief excerpts can still be missed.
