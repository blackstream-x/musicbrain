# Fixing the tag encoding with print_tracklist.py

In this example, mp3 metadata had been saved as UTF-8,
but the encoding had not been declared correctly by an old version of my
tagging program. This lead to the situation that the tags were read as
Latin-1 encoded, producing unreadable results as shown.

You can use the ```--fix-tag-encoding``` option to re-encode the tags
(letting taglib do the details).

```
$ ./print_tracklist.py -d testdata/A\ Hard\ Day’s\ Knight/
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ ═══╦════════════════════════════════╦════════════════════════════════════════════════
INFO    ║    ║ à;GRUMH… – A Hard Day’s Knight ║
INFO    ║    ╚════════════════════════════════╝
INFO    ║ ───┬───────────────────────────────────────────────────────┬─────────────────────────
INFO    ║    │ Medium #1: à;GRUMH… – A Hard Day’s Knight (10 tracks) │
INFO    ║    └───────────────────────────────────────────────────────┘
A1. Danger Zone – à;GRUMH… (06:26)
A2. Fly, Nun, Fly – à;GRUMH… (04:10)
A3. Silence Between Two Tracks – à;GRUMH… (00:11)
A4. Bucaresse – à;GRUMH… (07:13)
A5. à;GRUMH… - C.B.B. C.B.B. (14%) – à;GRUMH… (04:41)
B1. Spectral Cats – à;GRUMH… (03:01)
B2. Loco Loco (Nouveau Cock mix) – à;GRUMH… (04:17)
B3. Play It Loud! – à;GRUMH… (05:46)
B4. The March – à;GRUMH… (05:01)
B5. Chilly (Willy and His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes) – à;GRUMH… (04:21)
$
$
$ eyeD3 testdata/A\ Hard\ Day’s\ Knight/
...n/testdata/A Hard Day’s Knight/d1A1. à;GRUMH… - Danger Zone.mp3                      [ 8.86 MB ]
----------------------------------------------------------------------------------------------------
Time: 06:27	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Danger Zone
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 1/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...testdata/A Hard Day’s Knight/d1A2. à;GRUMH… - Fly, Nun, Fly.mp3                      [ 5.75 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:10	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Fly, Nun, Fly
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 2/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
... Day’s Knight/d1A3. à;GRUMH… - Silence Between Two Tracks.mp3                      [ 282.08 KB ]
----------------------------------------------------------------------------------------------------
Time: 00:11	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Silence Between Two Tracks
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 3/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...ain/testdata/A Hard Day’s Knight/d1A4. à;GRUMH… - Bucaresse.mp3                      [ 9.95 MB ]
----------------------------------------------------------------------------------------------------
Time: 07:15	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Bucaresse
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 4/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
.../testdata/A Hard Day’s Knight/d1A5. à;GRUMH… - C.B.B. (14%).mp3                      [ 6.46 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:42	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: C.B.B. (14%)
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 5/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...testdata/A Hard Day’s Knight/d1B1. à;GRUMH… - Spectral Cats.mp3                      [ 4.18 MB ]
----------------------------------------------------------------------------------------------------
Time: 03:02	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Spectral Cats
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 6/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
... Day’s Knight/d1B2. à;GRUMH… - Loco Loco (Nouveau Cock mix).mp3                      [ 5.91 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:17	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Loco Loco (Nouveau Cock mix)
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 7/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...testdata/A Hard Day’s Knight/d1B3. à;GRUMH… - Play It Loud!.mp3                      [ 7.95 MB ]
----------------------------------------------------------------------------------------------------
Time: 05:47	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Play It Loud!
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 8/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...ain/testdata/A Hard Day’s Knight/d1B4. à;GRUMH… - The March.mp3                      [ 6.92 MB ]
----------------------------------------------------------------------------------------------------
Time: 05:02	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: The March
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 9/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
... His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes).mp3                      [ 6.01 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:22	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Chilly (Willy and His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes)
artist: Ã ;GRUMHâ¦
album: A Hard Dayâs Knight
album artist: Ã ;GRUMHâ¦
recording date: 1989
track: 10/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
$
$
$ ./print_tracklist.py --fix-tag-encoding -d testdata/A\ Hard\ Day’s\ Knight/
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'A Hard Dayâ\x80\x99s Knight' -> 'A Hard Day’s Knight'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ Fixed 'Ã\xa0;GRUMHâ\x80¦' -> 'à;GRUMH…'
INFO    ║ ═══╦════════════════════════════════╦════════════════════════════════════════════════
INFO    ║    ║ à;GRUMH… – A Hard Day’s Knight ║
INFO    ║    ╚════════════════════════════════╝
INFO    ║ ───┬───────────────────────────────────────────────────────┬─────────────────────────
INFO    ║    │ Medium #1: à;GRUMH… – A Hard Day’s Knight (10 tracks) │
INFO    ║    └───────────────────────────────────────────────────────┘
A1. Danger Zone – à;GRUMH… (06:26)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1A1. à;GRUMH… - Danger Zone.mp3
A2. Fly, Nun, Fly – à;GRUMH… (04:10)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1A2. à;GRUMH… - Fly, Nun, Fly.mp3
A3. Silence Between Two Tracks – à;GRUMH… (00:11)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1A3. à;GRUMH… - Silence Between Two Tracks.mp3
A4. Bucaresse – à;GRUMH… (07:13)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1A4. à;GRUMH… - Bucaresse.mp3
A5. à;GRUMH… - C.B.B. C.B.B. (14%) – à;GRUMH… (04:41)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1A5. à;GRUMH… - C.B.B. (14%).mp3
B1. Spectral Cats – à;GRUMH… (03:01)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1B1. à;GRUMH… - Spectral Cats.mp3
B2. Loco Loco (Nouveau Cock mix) – à;GRUMH… (04:17)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1B2. à;GRUMH… - Loco Loco (Nouveau Cock mix).mp3
B3. Play It Loud! – à;GRUMH… (05:46)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1B3. à;GRUMH… - Play It Loud!.mp3
B4. The March – à;GRUMH… (05:01)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1B4. à;GRUMH… - The March.mp3
B5. Chilly (Willy and His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes) – à;GRUMH… (04:21)
INFO    ║ Saved tags to /home/rainer/projects/github/blackstream-x/musicbrain/testdata/A Hard Day’s Knight/d1B5. à;GRUMH… - Chilly (Willy and His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes).mp3
$
$
$ ./print_tracklist.py -d testdata/A\ Hard\ Day’s\ Knight/
INFO    ║ ═══╦════════════════════════════════╦════════════════════════════════════════════════
INFO    ║    ║ à;GRUMH… – A Hard Day’s Knight ║
INFO    ║    ╚════════════════════════════════╝
INFO    ║ ───┬───────────────────────────────────────────────────────┬─────────────────────────
INFO    ║    │ Medium #1: à;GRUMH… – A Hard Day’s Knight (10 tracks) │
INFO    ║    └───────────────────────────────────────────────────────┘
A1. Danger Zone – à;GRUMH… (06:26)
A2. Fly, Nun, Fly – à;GRUMH… (04:10)
A3. Silence Between Two Tracks – à;GRUMH… (00:11)
A4. Bucaresse – à;GRUMH… (07:13)
A5. à;GRUMH… - C.B.B. C.B.B. (14%) – à;GRUMH… (04:41)
B1. Spectral Cats – à;GRUMH… (03:01)
B2. Loco Loco (Nouveau Cock mix) – à;GRUMH… (04:17)
B3. Play It Loud! – à;GRUMH… (05:46)
B4. The March – à;GRUMH… (05:01)
B5. Chilly (Willy and His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes) – à;GRUMH… (04:21)
$
$
$ eyeD3 testdata/A\ Hard\ Day’s\ Knight/
...n/testdata/A Hard Day’s Knight/d1A1. à;GRUMH… - Danger Zone.mp3                      [ 8.86 MB ]
----------------------------------------------------------------------------------------------------
Time: 06:27	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Danger Zone
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 1/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...testdata/A Hard Day’s Knight/d1A2. à;GRUMH… - Fly, Nun, Fly.mp3                      [ 5.75 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:10	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Fly, Nun, Fly
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 2/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
... Day’s Knight/d1A3. à;GRUMH… - Silence Between Two Tracks.mp3                      [ 282.21 KB ]
----------------------------------------------------------------------------------------------------
Time: 00:11	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Silence Between Two Tracks
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 3/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...ain/testdata/A Hard Day’s Knight/d1A4. à;GRUMH… - Bucaresse.mp3                      [ 9.95 MB ]
----------------------------------------------------------------------------------------------------
Time: 07:15	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Bucaresse
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 4/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
.../testdata/A Hard Day’s Knight/d1A5. à;GRUMH… - C.B.B. (14%).mp3                      [ 6.46 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:42	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: C.B.B. (14%)
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 5/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...testdata/A Hard Day’s Knight/d1B1. à;GRUMH… - Spectral Cats.mp3                      [ 4.18 MB ]
----------------------------------------------------------------------------------------------------
Time: 03:02	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Spectral Cats
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 6/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
... Day’s Knight/d1B2. à;GRUMH… - Loco Loco (Nouveau Cock mix).mp3                      [ 5.91 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:17	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Loco Loco (Nouveau Cock mix)
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 7/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...testdata/A Hard Day’s Knight/d1B3. à;GRUMH… - Play It Loud!.mp3                      [ 7.95 MB ]
----------------------------------------------------------------------------------------------------
Time: 05:47	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Play It Loud!
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 8/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
...ain/testdata/A Hard Day’s Knight/d1B4. à;GRUMH… - The March.mp3                      [ 6.92 MB ]
----------------------------------------------------------------------------------------------------
Time: 05:02	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: The March
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 9/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
... His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes).mp3                      [ 6.01 MB ]
----------------------------------------------------------------------------------------------------
Time: 04:22	MPEG1, Layer III	[ 192 kb/s @ 44100 Hz - Joint stereo ]
----------------------------------------------------------------------------------------------------
ID3 v2.4:
title: Chilly (Willy and His Aerodynamic Kit) Bag (Thunderstorm Water of the Hopes)
artist: à;GRUMH…
album: A Hard Day’s Knight
album artist: à;GRUMH…
recording date: 1989
track: 10/10
disc: 1
FRONT_COVER Image: [Size: 22795 bytes] [Type: image/jpeg]
Description: a-grumh.a_hard_days_knight.front.jpg

----------------------------------------------------------------------------------------------------
$

```