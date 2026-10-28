"""Optional offline speech denoising using the pinned Hush native runtime."""
import array
import ctypes
import math
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import wave

MODEL_VERSION = "hush-v1.0.0"


class EnhancementCancelled(Exception):
    """Raised when the user cancels local enhancement."""


def _check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise EnhancementCancelled("Speech enhancement was cancelled.")


def _report(progress, value):
    if progress:
        progress(max(0, min(100, int(value))))


def _is_supported_wav(path):
    try:
        with wave.open(str(path), "rb") as source:
            return (source.getcomptype() == "NONE" and source.getnchannels() == 1
                    and source.getsampwidth() == 2 and source.getframerate() == 16000)
    except (wave.Error, OSError):
        return False


def _convert_to_mono_16k(source, output, app_dir, cancel, progress):
    from engine import VLC
    destination = pathlib.Path(output).resolve().as_posix().replace('"', r'\\"')
    sout = f'#transcode{{acodec=s16l,channels=1,samplerate=16000}}:std{{access=file,mux=wav,dst="{destination}"}}'
    decoder = None
    try:
        decoder = VLC(options=[f'--sout={sout}', '--sout-keep'])
        decoder.load(source)
        if decoder.play() < 0:
            raise RuntimeError("VLC could not start audio conversion.")
        started = time.monotonic()
        while True:
            _check_cancel(cancel)
            state = decoder.state()
            if state["status"] == "ended":
                break
            if state["status"] == "error":
                raise RuntimeError("VLC could not decode this recording for speech enhancement.")
            if state["status"] == "stopped" and time.monotonic() - started > 2:
                raise RuntimeError("VLC stopped before audio conversion finished.")
            duration = state.get("duration", 0)
            if duration > 0 and progress:
                try:
                    written = output.stat().st_size if output.exists() else 0
                    expected = max(1, round(duration * 16000 * 2) + 44)
                    _report(progress, min(9, round(9 * written / expected)))
                except OSError:
                    pass
            time.sleep(.08)
    finally:
        if decoder:
            decoder.close()
    if not output.is_file() or output.stat().st_size <= 44:
        raise RuntimeError("VLC could not convert this recording for speech enhancement.")
    if not _is_supported_wav(output):
        raise RuntimeError("The local converter did not produce the expected 16 kHz mono WAV.")
    _report(progress, 10)

def _bind(lib, name, result, args):
    function = getattr(lib, name)
    function.restype = result
    function.argtypes = args
    return function


def _process_wav(source_path, output_path, library_path, model_path, cancel, progress):
    if not _is_supported_wav(source_path):
        raise ValueError("Speech engine input must be uncompressed 16-bit mono 16 kHz WAV.")
    dll_directory = None
    model = None
    session = None
    lib = None
    try:
        if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
            dll_directory = os.add_dll_directory(str(pathlib.Path(library_path).resolve().parent))
        lib = ctypes.CDLL(str(library_path))
        _bind(lib, "weya_nc_model_load_from_path", ctypes.c_void_p, [ctypes.c_char_p])
        _bind(lib, "weya_nc_model_free", None, [ctypes.c_void_p])
        _bind(lib, "weya_nc_session_create", ctypes.c_void_p,
              [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_float])
        _bind(lib, "weya_nc_session_free", None, [ctypes.c_void_p])
        _bind(lib, "weya_nc_get_frame_length", ctypes.c_size_t, [ctypes.c_void_p])
        _bind(lib, "weya_nc_process_frame", ctypes.c_float,
              [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)])
        model = lib.weya_nc_model_load_from_path(os.fsencode(model_path))
        if not model:
            raise RuntimeError("The offline speech model could not be loaded.")
        session = lib.weya_nc_session_create(model, 16000, ctypes.c_float(35.0))
        if not session:
            raise RuntimeError("The offline speech processor could not start.")
        frame_length = int(lib.weya_nc_get_frame_length(session))
        if not 0 < frame_length <= 4096:
            raise RuntimeError("The speech processor returned an unsupported frame size.")
        input_buffer = (ctypes.c_float * frame_length)()
        output_buffer = (ctypes.c_float * frame_length)()
        last_progress = -1
        def report(value):
            nonlocal last_progress
            value = max(0, min(100, int(value)))
            if value != last_progress:
                last_progress = value
                _report(progress, value)
        with wave.open(str(source_path), "rb") as src:
            total = src.getnframes()
            if total <= 0:
                raise ValueError("This recording contains no audio.")
            with wave.open(str(output_path), "wb") as dst:
                dst.setnchannels(1)
                dst.setsampwidth(2)
                dst.setframerate(16000)
                done = 0
                while done < total:
                    _check_cancel(cancel)
                    raw = src.readframes(frame_length)
                    samples = array.array("h")
                    samples.frombytes(raw)
                    if sys.byteorder != "little":
                        samples.byteswap()
                    valid = len(samples)
                    if not valid:
                        break
                    samples.extend([0] * (frame_length - valid))
                    for i, sample in enumerate(samples):
                        input_buffer[i] = sample / 32768.0
                    lib.weya_nc_process_frame(session, input_buffer, output_buffer)
                    cleaned = array.array("h")
                    for value in output_buffer[:valid]:
                        value = float(value)
                        if not math.isfinite(value):
                            value = 0.0
                        cleaned.append(max(-32768, min(32767, round(max(-1.0, min(1.0, value)) * 32768))))
                    if sys.byteorder != "little":
                        cleaned.byteswap()
                    dst.writeframesraw(cleaned.tobytes())
                    done += valid
                    report(10 + round(85 * done / total))
        report(98)
    finally:
        if session and lib:
            lib.weya_nc_session_free(session)
        if model and lib:
            lib.weya_nc_model_free(model)
        if dll_directory:
            dll_directory.close()


def enhance_file(source, output, app_dir, cancel=None, progress=None):
    """Create a new enhanced WAV; never write to or replace the source recording."""
    source = pathlib.Path(source).resolve()
    output = pathlib.Path(output).resolve()
    app_dir = pathlib.Path(app_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError("The source recording is no longer available.")
    if source == output:
        raise ValueError("Enhanced output must be separate from the original recording.")
    library = app_dir / "runtime" / "speech" / "weya_nc.dll"
    model = app_dir / "runtime" / "speech" / "advanced_dfnet16k_model_best_onnx.tar.gz"
    if not library.is_file() or not model.is_file():
        raise RuntimeError("The offline speech engine is missing. Repair or reinstall Shiur Player.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="shiur-speech-", dir=str(output.parent)) as temporary:
        temporary = pathlib.Path(temporary)
        converted = source if _is_supported_wav(source) else temporary / "input.wav"
        if converted != source:
            _convert_to_mono_16k(source, converted, app_dir, cancel, progress)
        _check_cancel(cancel)
        processed = temporary / "enhanced.wav"
        _process_wav(converted, processed, library, model, cancel, progress)
        _check_cancel(cancel)
        with wave.open(str(processed), "rb") as result:
            if result.getnframes() <= 0 or result.getframerate() != 16000 or result.getnchannels() != 1:
                raise RuntimeError("The speech processor produced an invalid audio file.")
        os.replace(processed, output)
    _report(progress, 100)
    return output
