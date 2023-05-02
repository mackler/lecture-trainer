# Lecture Trainer

This is a Perl script that converts a text file into a sequence of
audio files that you can use to memorize a speech by ear, rather than
by reading it yourself.

## Requirements:

* perl (to run the script)
* espeak-ng (to generate the sound files)
* sox (to add silence to each sound file)
* lame (for mp3 encoding)

## Usage

The name of the source file must have the suffix `.txt` and its
contents must be text.  Each block of text separated by two (or more) newlines
will be converted to a separate sound file.  All sound files and
playlists will be written to a directory having the same name as the
source file except for the `.txt` suffix.  This output directory will be
created if necessary.

The name of the script is `render`, so

    ./render mylecture.txt

will create a directory named `mylecture` into which the resulting
sound and playlist files will go.  The sound files are numbered in
descending order, and two playlists are created named `backward.m3u`
and `forward.m3u`.  Each sound file is padded with silence so you can
listen and repeat while looping.

The suggested technique is to memorize the files in ascending
numerical order, that is in the reverse of the order in which you wish
to deliver the speech.  Learning your speech backwards makes it much
easier to catch yourself if you skip content when delivering the
speech in forward order.

Once you have generated the audio and playlist files, load them into a
sound-player application with play mode set to repeat a single file.
Start playing the first sound file in the playlist.  Listen and
repeat, listen and repeat.  After a few repetitions pause the player
and repeat on your own.  Proceed this way to memorize each sound file
in sequence, moving back and forth in the playlist to confirm your
memory.
