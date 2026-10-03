#!/usr/bin/env python3

import os
import re
import sys
import argparse
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


def render_clip(model, text, out_path, gen_kwargs):
    """Synthesize one chunk to an MP3 at out_path, with equal trailing silence."""
    wav = model.generate(text, **gen_kwargs)
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
        subprocess.run(["lame", "--quiet", tmpfile, out_path])
    finally:
        os.remove(tmpfile)


def parse_args():
    p = argparse.ArgumentParser(
        description="Synthesize a text file to numbered MP3 clips with Chatterbox."
    )
    p.add_argument("input", help="UTF-8 text file")
    p.add_argument(
        "voice", nargs="?", default=None,
        help="optional reference WAV for voice cloning",
    )
    p.add_argument(
        "-c", "--clip", type=int, default=None,
        help="regenerate only this clip number; leaves the playlists unchanged",
    )
    return p.parse_args()


def main():
    args = parse_args()
    file = args.input
    voice = args.voice
    clip = args.clip

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

    # Clip number equals the output filename number: clip 0 is the last piece,
    # clip 1 the second-to-last, and so on. Regeneration reproduces the same
    # filename only when the piece count is unchanged from the full run.
    if clip is not None and not (0 <= clip < count):
        sys.stderr.write(f"clip number {clip} out of range 0..{count - 1}\n")
        sys.exit(1)

    print("Loading Chatterbox model on CPU")
    model = ChatterboxTTS.from_pretrained(device="cpu")

    gen_kwargs = {}
    if voice:
        gen_kwargs["audio_prompt_path"] = voice

    targets = [clip] if clip is not None else range(count)

    backward_lines = []
    forward_lines = []

    for i in targets:
        outfile = f"{i:0{count_places}d}.mp3"
        print(f"{i}. ", end="", flush=True)
        index = count - 1 - i

        piece = re.sub(r"[\n\r]+", " ", pieces[index])
        if debug:
            print(piece)

        render_clip(model, piece, os.path.join(outdir, outfile), gen_kwargs)

        backward_lines.append(outfile)
        forward_lines.append(f"{index:0{count_places}d}.mp3")

    print()

    # Rewrite the playlists only on a full run. A single-clip regeneration does
    # not change their contents, so they are left in place.
    if clip is None:
        write_atomic(os.path.join(outdir, "backward.m3u"), backward_lines)
        write_atomic(os.path.join(outdir, "forward.m3u"), forward_lines)


if __name__ == "__main__":
    main()
