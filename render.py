#!/usr/bin/env python3

import os
import re
import sys
import tempfile
import subprocess

import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS


def write_atomic(path, lines):
    """Write lines to path via a temp file in the same directory, then rename."""
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.writelines(f"{line}\n" for line in lines)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def main():
    if len(sys.argv) < 2 or not sys.argv[1]:
        sys.stderr.write(f"usage: {sys.argv[0]} <textfile-name> [voice-wav]\n")
        sys.exit(1)

    file = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None

    print(f"Reading from {file}")

    with open(file, "r", encoding="utf-8") as fh:
        text = fh.read()

    debug = True

    # Strip any leading path and the .txt suffix; produce audio/<basename>.
    # If the name does not end in .txt, outdir remains equal to file.
    outdir = re.sub(r"^(.*/)?([^/]+)\.txt$", r"audio/\2", file)

    if not os.path.isdir("audio"):
        os.mkdir("audio")
    if not os.path.isdir(outdir):
        os.mkdir(outdir)
    print(f"Writing audio files to {outdir}")

    pieces = re.split(r"\n{2,}", text)

    count = len(pieces)
    count_places = len(str(count))

    print("Loading Chatterbox model on CPU")
    model = ChatterboxTTS.from_pretrained(device="cpu")

    gen_kwargs = {}
    if voice:
        gen_kwargs["audio_prompt_path"] = voice

    backward_lines = []
    forward_lines = []

    for i in range(count):
        outfile = f"{i:0{count_places}d}.mp3"
        print(f"{i}. ", end="", flush=True)
        index = count - 1 - i

        piece = re.sub(r"[\n\r]+", " ", pieces[index])
        if debug:
            print(piece)

        # Synthesize speech with Chatterbox. generate() returns a float tensor.
        wav = model.generate(piece, **gen_kwargs)
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)

        # Append trailing silence equal in sample count to the generated audio.
        silence = torch.zeros(
            wav.shape[0], wav.shape[-1], dtype=wav.dtype, device=wav.device
        )
        padded = torch.cat([wav, silence], dim=1)

        # Write a temporary 16-bit PCM WAV, then encode it to MP3 with lame.
        fd, tmpfile = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            ta.save(tmpfile, padded, model.sr, encoding="PCM_S", bits_per_sample=16)
            subprocess.run(
                ["lame", "--quiet", tmpfile, os.path.join(outdir, outfile)],
            )
        finally:
            os.remove(tmpfile)

        backward_lines.append(outfile)
        forward_lines.append(f"{index:0{count_places}d}.mp3")

    print()

    # Write both playlists only after every MP3 exists. Each write is atomic:
    # the final name never refers to a partial file.
    write_atomic(os.path.join(outdir, "backward.m3u"), backward_lines)
    write_atomic(os.path.join(outdir, "forward.m3u"), forward_lines)


if __name__ == "__main__":
    main()
