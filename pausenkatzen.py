import vlc
from vlc import VideoMarqueeOption
from vlc import Position
#from vlc import str_to_bytes
from time import sleep
import threading
from dateutil.parser import parse
import os.path
from VideoPool import VideoPool
from CccStreamIndexer import CccStreamIndexer
from IcsStreamIndexer import IcsStreamIndexer
from Streamer import Streamer
from Mosaic import Mosaic

# Initialize helpers
videopool = VideoPool( os.path.expanduser("~/Videos/*.mp4"), refreshInterval=900 )
streamIndexer = CccStreamIndexer( uri="https://fahrplan.events.ccc.de/camp/2019/Fahrplan/schedule.json", margin=300, refreshInterval=1700 )
#streamIndexer = IcsStreamIndexer( uri="https://calendar.google.com/calendar/ical/urcks8dad8c2437selb600pm10%40group.calendar.google.com/public/basic.ics", margin=300, refreshInterval=1700 )
streamer = Streamer( uri="https://cdn.c3voc.de/hls/s{}_native_sd.m3u8", address="239.255.255.42", refreshInterval=0.5 )
mosaic = Mosaic( uri="ACKflag.png", address="239.255.255.42", refreshInterval=0.5, startPort=9001, outPort=5004 )

roomsStreaming = {}

rooms = streamIndexer.getStreamLocations( )
for room in rooms:
    roomsStreaming[ room ] = False

def playEvent( room, state ):
    print ( room, state )
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
    roomsBusy = streamIndexer.getActiveStreams( )
    # Iterate the complete list of rooms and check against the current active streams 
    for room in roomsStreaming:
        busy = room in roomsBusy and roomsBusy[ room ]

        #print ( "#room {}: streaming={} busy={}".format( room, roomsStreaming[ room ], busy ) )
        if ( not busy and roomsStreaming[ room ] ):
            # Switch stream
            print( room + " switching to intermezzo" )
            streamer.setActive( room, False )
            # Store status
            roomsStreaming[ room ] = False
        if ( busy and not roomsStreaming[ room ] ):
            print( room + " switching to active" )
            # Switch stream
            streamer.setActive( room, True )
            # Store status
            roomsStreaming[ room ] = True

streamer.attachEvent( playEvent )
streamer.setStreams( rooms )

mosaic.setStreams( rooms )

# Kick off the streams
for room in streamIndexer.getStreamLocations():
    streamer.setIntermezzo( room, videopool.randomVideo() )
    streamer.setActive( room, False )
    mosaic.setActive( room, True )

setInterval( checkBusy, 60 )
checkBusy()

