import vlc
from vlc import VideoMarqueeOption
from vlc import Position
#from vlc import str_to_bytes
from time import sleep
import threading
from dateutil.parser import parse

from VideoPool import VideoPool
from StreamIndexer import StreamIndexer
from Streamer import Streamer

# Initialize helpers
videopool = VideoPool( "/home/xopr/Videos/*.mp4")
streamIndexer = StreamIndexer( uri="https://fahrplan.events.ccc.de/camp/2019/Fahrplan/schedule.json", margin=300, refreshInterval=1700 )
streamer = Streamer( uri="https://cdn.c3voc.de/hls/s{}_native_sd.m3u8", address="239.255.255.42", refreshInterval=0.5 )

roomsStreaming = {}

rooms = streamIndexer.getRooms( )
for room in rooms:
    roomsStreaming[ room ] = False

def playEvent( room, state ):
    if ( state == "stopped" ): 
        if ( roomsStreaming[ room ] ):
            # Active room stopped, restart stream
            print( "NOTE: Active room stream stopped, restarting" ) 
            streamer.setActive( room, True )
        else:
            # room intermezzo stopped, feed new video
            streamer.setIntermezzo( room, videopool.randomVideo() )
            streamer.setActive( room, False )


def setInterval(func, sec):
    def func_wrapper():
        setInterval( func, sec )
        func()
    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t


def checkBusy():
    roomsBusy = streamIndexer.getActiveTalks( )

    for room in roomsBusy:
        if ( not roomsBusy[ room ] and roomsStreaming[ room ] ):
            # Switch stream
            print( room + " switching to intermezzo" )
            streamer.setActive( room, False )
            # Store status
            roomsStreaming[ room ] = False
        if ( roomsBusy[ room ] and not roomsStreaming[ room ] ):
            print( room + " switching to active" )
            # Switch stream
            streamer.setActive( room, True )
            # Store status
            roomsStreaming[ room ] = True

streamer.attachEvent( playEvent )
streamer.setStreams( rooms )

# Kick off the streams
for room in streamIndexer.getRooms():
    streamer.setIntermezzo( room, videopool.randomVideo() )
    streamer.setActive( room, False )

setInterval( checkBusy, 60 )
checkBusy()

