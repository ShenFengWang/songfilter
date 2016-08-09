#! /usr/bin/python3
import subprocess
import os
def deleteSong():
    songPath = subprocess.check_output(["audtool", "current-song-filename"]).decode("utf8").strip()
    songPosition = subprocess.check_output(["audtool", "playlist-position"]).decode("utf8").strip()
    if songPath == "No song playing.":
        print(songPath)
        return False
    print(songPath)
    print(songPosition)

    subprocess.call(["audtool", "playlist-delete", songPosition])
    os.remove(songPath)

def run():
    subprocess.call(["audtool", "playback-play"])

if __name__ == "__main__":
    import argparse
    commandParser = argparse.ArgumentParser()
    commandParser.add_argument('-D', '--delete', action = 'store_true')
    args = commandParser.parse_args()
    if args.delete:
        deleteSong()
        run()


