# pausenkatzen
*Multicast pollution if there is no active conference*

## synopsis
read [Chaos Communication Congress/Camp](https://streaming.media.ccc.de) schedule and set up multicast streams for each room/stage.  Transmit a random video from a pool when there is no talk broadcasted (also known as '[pausenkatzen](https://www.youtube.com/watch?v=kg2fwlFsZss)' or: 'intermission cats').

## prerequisites
* VLC media player (preferrably version < 2.2, see notes)
* local collection of video material
* python (python3 in the works)
* python libraries (some are packaged with python):
  * collections
  * datetime
  * dateutil
  * glob
  * json
  * random
  * requests
  * threading
  * time
  * vlc

## setup
* install `vlc` and the `python-vlc` module/package
* clone this repository
* edit `pausenkatzen.py`: verify that
  * VideoPool points to an existing directory containing videos
  * StreamIndexer points to a current CCC schedule
  * Streamer points to a corresponding working stream (note that `{}` will be replaced by a number, increased for each new stream)
* run `python pausenkatzen.py`

## notes
* every time a new video is injected to transmit, the multicast will hiccup and buffer for a couple of seconds; short videos will not have the desired effect you were looking for.
* with trial and error, we came to conclusion that VLC >= 3.x has issues with HLS streams, VLC >= 2.2 has issues with creating the mosaic.
