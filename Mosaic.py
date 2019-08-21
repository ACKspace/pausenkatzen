import rsvg
import cairo
import math
import numpy
import vlc
from vlc import VideoMarqueeOption
from vlc import Position
import threading
import json
from collections import namedtuple
StreamInfo = namedtuple("StreamInfo", "index sout name uri playing intermezzoUri")

#sout = "#rtp{{mux=ts,dst={0},port={1},sdp=sap://,name=\\\"Saal {2}\\\"}}"
sout = "#duplicate{{dst=mosaic-bridge{{id={1}}},select=video,dst=mosaic-bridge{{id={1}}},select=audio}}"
sout_mosaic = "#transcode{{sfilter=mosaic,vcodec=mp2v,vb=500,scale=1}}:bridge-in{{delay=400,id-offset=100}}:rtp{{mux=ts,dst={0},port={1},sap,name=\\\"{2}\\\"}}"

streamName = "saal{}"

class Mosaic:
    """Constructor

    Args:
        uri (str or unicode): Path/unified resource to background
        address (str or unicode): Multicast IP address
        refreshInterval (int): Refresh interval for checking current streaming state
        startPort (int): The first IP port where the streams can be found
        outPort (int): The IP port to multicast the mosaic on
    """
    def __init__(self, uri="PM5644.svg", address="239.255.255.42", refreshInterval=2, startPort=9001, outPort=5004):
        # NOTE: some examples used split()
        self.instance=vlc.Instance('--verbose 0 -q --fullscreen --mosaic-width 1280 --mosaic-order "1,2,3,4,9,5,6,7,8" --mosaic-height 720' )

        self.uri = uri
        self.address = address
        self.interval = refreshInterval
        self.startPort = startPort
        self.outPort = outPort


    """Set streams to put in the mosaic

    This will generate a mosaic background with as many named testcards as there are streams.
    It also creates an extra stream that contains the merged streams, a.k.a. the mosaic.
    This mosaic will be send out as multicast on the designated port

    Args:
        streamNames (list[str]): Names for each stream (as used in the testcard description)
    """
    def setStreams(self, streamNames):

        n = 1;
        self.streamNames = {}
        for stream in streamNames:
            streamInfo = StreamInfo( n, sout.format( self.address, self.startPort + n - 1, stream ), streamName.format(n), self.uri.format(n), False, None )
            self.streamNames[ stream ] = streamInfo

            self.instance.vlm_add_broadcast( streamInfo.name, streamInfo.uri, streamInfo.sout, 0, [], True, False)

            print( "Adding: " + stream )

            n += 1

        mosaicOrder = self.generateBackground( streamNames )

        #new background broadcast enabled
        #setup background input fake:
        #setup background option mosaic-width=800
        #setup background option mosaic-height=300
        #setup background option mosaic-rows=1
        #setup background option mosaic-cols=2
        #setup background option mosaic-position=1
        #setup background option mosaic-order="1,2"
        #1,2,0,0,0,0
        #setup background option fake-file="back.gif"
        #setup background option fake-width=800
        #setup background option fake-height=300
        #setup background option fake-fps="8"
        options = ["image-duration=-1", "image-fps=24/1", "mosaic-position=1"]
        self.instance.vlm_add_broadcast( "mosaic", self.uri, sout_mosaic.format( self.address, self.outPort, "Mosaic" ), 0, options, True, False)

        print( "New stream: " + "Mosaic" + "\trtp://@" + self.address + ":{}".format( self.outPort ) )
        print("")
 
        self.setInterval( self.checkPlaying, self.interval )
        self.checkPlaying()


    def generateBackground(self, streamNames):
        # Determine thumbnail layout (nxn, distribute evenly)
        mosaicOrder = ""
        sep = ""

        tiles=len( streamNames )
        maxTiles = int(math.ceil(math.sqrt( tiles )))
        maxTiles *= maxTiles
        activeTiles = numpy.around(numpy.linspace(1, maxTiles, num=tiles))

        svg_data=""
        with open(self.uri) as f:
            svg_data = str(f.read())
        #svg_surface = cairo.SVGSurface(None, width, height)
        width = 1280
        height = 720
        svg_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        svg_context = cairo.Context(svg_surface)

        for i in range(1, maxTiles+1):
            if ( not i in activeTiles ):
                mosaicOrder += sep + "0"
            else:
                mosaicOrder += sep + str( i )
                # TODO: Generate thumbnail and place on background
                # TODO: take intermezzoUri into account
                # TODO: file read/url request

                # TODO: set title(s)
                #"s/LDO TV/${TEXT[0]}/g"

                #Optionally (subtitle)
                #"s/\(<\!--\|-->\)//g"
                #"s/DIGITAL/${TEXT[1]}/g"
                svg_handle = rsvg.Handle( None, svg_data)

                svg_width = svg_handle.props.width
                svg_height = svg_handle.props.height

                # Draw svg
                svg_context.save()
                # TODO: svg_context.translate( n, n) before/after scale
                svg_context.scale(float(width)/svg_width, float(height)/svg_height)
                svg_handle.render_cairo(svg_context)
                svg_context.restore()

            sep = ","

        svg_surface.write_to_png('mosaic_gen.png')

        return mosaicOrder
 

    def checkPlaying(self):
        for room in self.streamNames:
            stream = self.streamNames[ room ]

            # Get stream instance info
            state = json.loads(self.instance.vlm_show_media( stream.name ) )
            playing = state[ "instances" ] and (state[ "instances" ][ "instance" ][ "state" ] == "playing")

            if ( stream.playing and not playing and self.callback):
                self.callback( room, "stopped" )

            if ( stream.playing != playing ):
                self.streamNames[ room ] = stream._replace(playing=playing)


    """Set certain stream active or stop it to display the testcard

    This allows one to either display a certain stream or show the testcard,
    for example, to save (incoming) bandwidth.

    Args:
        streamName (str or unicode): The name of the stream to set active or inactive
        active (bool): Wheter to read and display the stream or show a testcard if False
    """
    def setActive(self, streamName, active):
        streamInfo = self.streamNames[ streamName ]

        if ( active ):
            self.instance.vlm_play_media( streamInfo.name )
        else:
            self.instance.vlm_stop_media( streamInfo.name )


    """Set intermezzo background (testcard)

    This allows one to set a custom background for a given stream which will be displayed
    when there is no incoming stream or if the stream is deactivated.

    Args:
        streamName (str): The name of the stream to set active or inactive
        uri (str or unicode): Path/unified resource to intermezzo background
    """
    def setIntermezzo(self, streamName, uri):
        print( "New intermezzo for " + streamName )
        self.streamNames[ streamName ] = self.streamNames[ streamName ]._replace(intermezzoUri=uri)


    """Register a callback function

    Store a callback function to call when there is an update on the incoming streams.

    Args:
        func (function): The callback function
    """
    def attachEvent(self, callback):
        self.callback = callback


    """Callback a function after determined amount of seconds

    Args:
        func (function): The callback function
        sec (int): The timeout in seconds after which the callback is called

    Returns:
        Timer: The timer instance that is started

    """
    def setInterval(self, func, sec):
        def func_wrapper():
            self.setInterval( func, sec )
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t

