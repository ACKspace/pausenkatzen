import cairo
#import rsvg
from gi import require_version
require_version('Rsvg', '2.0')
from gi.repository import Rsvg as rsvg
from ctypes import *
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
sout = "#duplicate{{dst=mosaic-bridge{{id={0}}},select=video,dst=mosaic-bridge{{id={0}}},select=audio}}"
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
    def __init__(self, uri="bg.png", address="239.255.255.42", refreshInterval=2, startPort=9001, outPort=5004):
        # NOTE: some examples used split()
        self.instance=vlc.Instance('--verbose 0 -q --fullscreen --mosaic-width 1280 --mosaic-order "1,2,3,4,9,5,6,7,8" --mosaic-height 720 --image-duration=-1 --image-fps=24/1 --mosaic-position=1' )

        self.uri = uri
        self.address = address
        self.interval = refreshInterval
        self.startPort = startPort
        self.outPort = outPort

        self.callback = None


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
            #                    index  sout name uri playing intermezzoUri")
            rtpUri = "rtp://" + self.address + ":" + str( self.startPort + n - 1 )
            streamInfo = StreamInfo( n, sout.format(n), streamName.format(n), rtpUri, False, "PM5644.svg" )
            self.streamNames[ stream ] = streamInfo

            self.instance.vlm_add_broadcast( streamInfo.name, streamInfo.uri, streamInfo.sout, 0, [], True, False)

            print( "Adding: " + stream + " to mosaic" )

            n += 1

        mosaicOrder = self.generateBackground( streamNames )
        #print( mosaicOrder )

        #Failed to open VDPAU backend libvdpau_va_gl.so: cannot open shared object file: No such file or directory

        options = [b'image-duration=-1', b'image-fps=24/1', b'mosaic-position=1', bytes("mosaic-order=" + mosaicOrder, encoding="utf8" )]
        #options = []
        self.instance.vlm_add_broadcast( "mosaic", "/home/xopr/Projects/pausenkatzen/mosaic_gen.png", sout_mosaic.format( self.address, self.outPort, "Mosaic" ), len(options), options, True, False)
        self.instance.vlm_play_media( "mosaic" )

        print( "New stream: " + "Mosaic" + "\trtp://@" + self.address + ":{}".format( self.outPort ) )
        print("")

        self.setInterval( self.checkPlaying, self.interval )
        self.checkPlaying()


    """Generates a mosaic background with testcards 

    Args:
        streamNames (list[str]): The list of stream names to generate testcards for

    Returns:
        str: A string that represents a VLC mosaic order across the image
    """
    def generateBackground(self, streamNames):
        # Determine thumbnail layout (nxn, distribute evenly)
        mosaicOrder = ""
        sep = ""

        tiles=len( streamNames )
        edgeTiles = int(math.ceil(math.sqrt( tiles )))
        maxTiles = edgeTiles * edgeTiles
        activeTiles = list(numpy.around(numpy.linspace(1, maxTiles, num=tiles)))

        # TODO: file read/url request
        svg_data=""
        # TODO: take intermezzoUri into account
        with open("PM5644.svg") as f:
            svg_data = str(f.read())
        #svg_surface = cairo.SVGSurface(None, width, height)
        width = 1280
        height = 720
        svg_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        svg_context = cairo.Context(svg_surface)
        # TODO: add bg: self.uri
        for i in range(1, maxTiles+1):
            if ( not i in activeTiles ):
                mosaicOrder += sep + "0"
            else:
                roomIndex = activeTiles.index( i )
                mosaicOrder += sep + str( roomIndex + 1 )

                custom_svg_data = svg_data.replace("LDO TV", streamNames[ roomIndex ] )
                # TODO: set subtitle
                #"s/\(<\!--\|-->\)//g"
                #"s/DIGITAL/${TEXT[1]}/g"

                #svg_handle = rsvg.Handle( None, svg_data)
                svg_handle = rsvg.Handle.new_from_data(bytes(custom_svg_data,encoding='utf8'))
                svg_width = svg_handle.props.width
                svg_height = svg_handle.props.height

                # Draw svg
                svg_context.save()
                x = (i-1) % edgeTiles
                y = int((i-1)/edgeTiles)
                svg_context.translate( x * width / edgeTiles, y * height / edgeTiles )
                svg_context.scale(float(width)/svg_width/edgeTiles, float(height)/svg_height/edgeTiles)
                #svg_context.translate( 900, 100 )
                svg_handle.render_cairo(svg_context)
                svg_context.restore()

            sep = ","

        svg_surface.write_to_png("mosaic_gen.png")

        return mosaicOrder
 

    def checkPlaying(self):
        #state = json.loads(self.instance.vlm_show_media( "mosaic" ) )
        #print( state )

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
        print( streamInfo.uri )
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

