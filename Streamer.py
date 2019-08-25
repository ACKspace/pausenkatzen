import vlc
from vlc import VideoMarqueeOption
from vlc import Position
import threading
import json
from collections import namedtuple
StreamInfo = namedtuple("StreamInfo", "index sout name uri playing intermezzoName intermezzoUri intermezzoPlaying")

sout = "#rtp{{mux=ts,dst={0},port={1},sdp=sap://,name=\\\"Saal {2}\\\"}}"
streamName = "saal{}"
intermezzoStreamName = "intermezzo{}"

class Streamer:
    def __init__(self, uri="https://cdn.c3voc.de/hls/s{}_native_sd.m3u8", address="239.255.255.42", refreshInterval=2):
        # NOTE: some examples used split()
        self.instance=vlc.Instance('--verbose 0 -q --fullscreen --sub-source marq' )

        self.address = address
        self.interval = refreshInterval
        self.uri = uri


    def setStreams(self, streamNames):
        n = 1;
        self.streamNames = {}
        for stream in streamNames:
            streamInfo = StreamInfo( n, sout.format( self.address, 9000+n, stream ), streamName.format(n), self.uri.format(n), False, intermezzoStreamName.format(n), "emptyURI", False )
            self.streamNames[ stream ] = streamInfo

            self.instance.vlm_add_broadcast( streamInfo.name, streamInfo.uri, streamInfo.sout, 0, [], True, False)
            self.instance.vlm_add_broadcast( streamInfo.intermezzoName, streamInfo.intermezzoUri, streamInfo.sout, 0, [], True, False)

            # rtp://@239.255.255.42:9001
            print( "New stream: " + stream + "\trtp://@" + self.address + ":{}".format( 9000+n ) )

            n += 1
        print("")
 
        self.setInterval( self.checkPlaying, self.interval )
        self.checkPlaying()


    def checkPlaying(self):
        for room in self.streamNames:
            stream = self.streamNames[ room ]

            # Get stream instance info
            state = self.instance.vlm_show_media( stream.name )
            #print( state )
            try:
                state = json.loads( state )
                playing = state[ "instances" ] and (state[ "instances" ][ "instance" ][ "state" ] == "playing")
            except:
                print( "stream info could not be decoded:" )
                print( state )
                print( "skipping" )
                playing = None

            intermezzoState = self.instance.vlm_show_media( stream.intermezzoName )
            try:
                intermezzoState = json.loads( intermezzoState )
                intermezzoPlaying = intermezzoState[ "instances" ] and (intermezzoState[ "instances" ][ "instance" ][ "state" ] == "playing")
            except:
                print( "intermezzo info could not be decoded:" )
                print( state )
                print( "skipping" )
                intermezzoPlaying = None

            if ( stream.playing or stream.intermezzoPlaying ):
                if ( not playing and not intermezzoPlaying and self.callback):
                    self.callback( room, "stopped" )

            if ( stream.playing != playing ):
                self.streamNames[ room ] = stream._replace(playing=playing)
            if ( stream.intermezzoPlaying != intermezzoPlaying ):
                self.streamNames[ room ] = stream._replace(intermezzoPlaying=intermezzoPlaying)


    def setActive(self, streamName, active):
        streamInfo = self.streamNames[ streamName ]

        if ( active ):
            self.instance.vlm_play_media( streamInfo.name )
            self.instance.vlm_stop_media( streamInfo.intermezzoName )
        else:
            self.instance.vlm_play_media( streamInfo.intermezzoName )
            self.instance.vlm_stop_media( streamInfo.name )


    def setIntermezzo(self, streamName, uri):
        if ( not uri ):
            return
        print( "New intermezzo for " + streamName )
        streamInfo = self.streamNames[ streamName ]
        self.instance.vlm_set_input( streamInfo.intermezzoName, uri )


    def attachEvent(self, callback):
        self.callback = callback


    def setInterval(self, func, sec):
        def func_wrapper():
            self.setInterval( func, sec )
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t

