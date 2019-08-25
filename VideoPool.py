import glob
import random
import threading

class VideoPool:
    def __init__(self, path, refreshInterval=0):
        self.list = []
        self.popList = []
        self.path = path
        self.refreshInterval = refreshInterval
        self.update()

        # 0 means realtime
        if ( self.refreshInterval ):
            self.setInterval( self.update, self.refreshInterval )

    def setInterval(self, func, sec):
        def func_wrapper():
            self.setInterval( func, sec )
            func()
        t = threading.Timer(sec, func_wrapper)
        t.start()
        return t

    def update(self):
        listcount = len( self.list )
        self.list = glob.glob(self.path)
        if ( not len( self.popList ) ):
            self.popList = self.list[:]

        # Only show delta
        if ( len( self.list ) > listcount ):
            print( "VideoPool found {} new files".format( len( self.list ) - listcount ) )
            print( "" )
        elif (len( self.list ) < listcount):
            print( "VideoPool lost {} files".format( listcount - len( self.list )) )
            print( "" )
            # TODO: remove LOST files on popList as well (to prevent video stall)
            self.popList = self.list[:]

    def randomVideo(self):
        if ( not self.refreshInterval ):
            self.update()

        if ( not len(self.list) ):
            return False

        if ( not len(self.popList) ):
            self.popList = self.list[:]

        randomChoice = self.popList.pop(random.randrange(len(self.popList)))

        return randomChoice
