#!/bin/bash
# capnote.sh <suffix> <pose>  : captures with-note and bare (note moved away in PIE) at the pose
SC="C:/Users/heman/AppData/Local/Temp/claude/C--Hemant-Prj-Learning-TheLastBell/be0022a0-87e7-4517-81e3-bd2aaebbbccb/scratchpad/r2c"
P=/c/Users/heman/AppData/Local/Python/pythoncore-3.14-64/python.exe
cd $SC
MSYS_NO_PATHCONV=1 timeout 60 $P pie_note.py home >/dev/null
timeout 100 bash cap.sh Docs/ArtTest/crypt r2c_ "$1" Tools/crypt/poses/r2c_poses.json $2 --force
MSYS_NO_PATHCONV=1 timeout 60 $P pie_note.py away >/dev/null
timeout 100 bash cap.sh Docs/ArtTest/crypt r2c_ "$1_bare" Tools/crypt/poses/r2c_poses.json $2 --force
MSYS_NO_PATHCONV=1 timeout 60 $P pie_note.py home
