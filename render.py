#!/usr/bin/env python3

import os
import re
import sys
import tempfile
import subprocess


def main():
    if len(sys.argv) < 2 or not sys.argv[1]:
        sys.stderr.write(f"usage: {sys.argv[0]} <textfile-name>\n")
        sys.exit(1)

    file = sys.argv[1]
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

    backward = open(os.path.join(outdir, "backward.m3u"), "w")
    forward = open(os.path.join(outdir, "forward.m3u"), "w")

    for i in range(count):
        outfile = f"{i:0{count_places}d}.mp3"
        print(f"{i}. ", end="", flush=True)
        index = count - 1 - i

        piece = re.sub(r"[\n\r]+", " ", pieces[index])
        if debug:
            print(piece)

        # Synthesize speech. espeak-ng writes WAV bytes to stdout.
        espeak = subprocess.run(
            ["espeak-ng", "--stdout"],
            input=piece.encode("utf-8"),
            stdout=subprocess.PIPE,
        )
        sound = espeak.stdout
        if espeak.returncode != 0:
            sys.exit(f'Failed to synthesize "{piece}"\n')

        # Measure clip length. sox reports statistics on stderr.
        stat = subprocess.run(
            ["sox", "-", "-n", "stat"],
            input=sound,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        match = re.search(
            r"Length \(seconds\):\s*([0-9.]+)",
            stat.stderr.decode("utf-8", errors="replace"),
        )
        if not match:
            sys.exit("could not determine clip length from sox output\n")
        seconds = match.group(1)

        # Append trailing silence equal to the clip length, then encode to MP3.
        fd, tmpfile = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            subprocess.run(
                ["sox", "-", tmpfile, "pad", "0", seconds],
                input=sound,
            )
            subprocess.run(
                ["lame", "--quiet", tmpfile, os.path.join(outdir, outfile)],
            )
        finally:
            os.remove(tmpfile)

        backward.write(f"{outfile}\n")
        forward.write(f"{index:0{count_places}d}.mp3\n")

    print()

    backward.close()
    forward.close()


if __name__ == "__main__":
    main()
