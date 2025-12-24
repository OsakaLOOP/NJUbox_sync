from anitopy import parse

filenames = [
    "[SubsPlease] Shingeki no Kyojin - The Final Season - 28 (1080p) [0A2B3C4D].mkv",
    "Frieren - S01E10.mkv",
    "[HorribleSubs] One Piece - 123 [1080p].mkv"
]

for f in filenames:
    print(f"Original: {f}")
    print(parse(f))
    print("-" * 20)
