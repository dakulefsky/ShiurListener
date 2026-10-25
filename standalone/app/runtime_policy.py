"""Explicit module set for the portable local-audio VLC runtime. This is not an OS sandbox."""
GROUPS={'audio_filter','audio_mixer','logger'}
FILES={
'access':{'libfilesystem_plugin'},
'audio_output':{'libadummy_plugin','libdirectsound_plugin','libmmdevice_plugin','libwasapi_plugin','libwaveout_plugin'},
'codec':{'libavcodec_plugin','libopus_plugin','libmpg123_plugin','libfaad_plugin','libspeex_plugin','libvorbis_plugin','libflac_plugin','libaraw_plugin'},
'demux':{'libau_plugin','libes_plugin','libmpc_plugin','libasf_plugin','libogg_plugin','libcaf_plugin','libaiff_plugin','libmp4_plugin','libwav_plugin','libtta_plugin','libflacsys_plugin','libvoc_plugin'},
'packetizer':{'libpacketizer_copy_plugin','libpacketizer_mpegaudio_plugin','libpacketizer_mpeg4audio_plugin','libpacketizer_flac_plugin','libpacketizer_mlp_plugin','libpacketizer_dts_plugin','libpacketizer_a52_plugin'},
'stream_filter':{'libinflate_plugin','libskiptags_plugin','libcache_block_plugin','libcache_read_plugin','libprefetch_plugin'},
'misc':{'libstats_plugin','liblogger_plugin'},
}
def allowed_plugin(category,stem):return category in GROUPS or stem in FILES.get(category,set())
def allowed_windows_file(path):
 parts=path.parts
 if len(parts)==1:return path.suffix.lower() in ('.dll','.txt')
 return len(parts)==3 and parts[0]=='plugins' and path.suffix.lower()=='.dll' and allowed_plugin(parts[1],path.stem)
