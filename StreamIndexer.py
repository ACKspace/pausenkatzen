import json
import requests
import threading
import datetime
from dateutil.parser import parse
from dateutil.tz import tzoffset

class StreamIndexer:
    def __init__(self, uri, margin=300, refreshInterval=0):
        self.uri = uri
        self.refreshInterval = refreshInterval
        self.margin = datetime.timedelta(hours=0, minutes=0, seconds=margin)

        self.update()

        # 0 means one time
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
        response = requests.get(self.uri)
        self.schedule = json.loads(response.text)

    def getRooms(self):
        rooms = []
        if ( self.schedule ):
            for i in self.schedule["schedule"]["conference"]["days"][1]["rooms"]:
                rooms.append( i )
        return rooms

    def getActiveTalks(self,timestamp=datetime.datetime.now(tzoffset('UTC+2', 2*3600))):
        if ( not self.schedule ):
            return {}

        rooms = {}

        # Distill active talks
        for d in self.schedule["schedule"]["conference"]["days"]:
            for r in d["rooms"]:
                if ( not r in rooms ):
                    rooms[ r ] = None

                for t in d["rooms"][ r ]:
                    start = parse( t[ "date" ] ) - self.margin
                    end = parse( t[ "duration" ] )
                    end = start + datetime.timedelta( hours=end.hour, minutes=end.minute ) + self.margin + self.margin

                    if ( not t[ "do_not_record" ] ):
                        if ( timestamp > start and timestamp < end ):
                            rooms[ r ] = t[ "title" ]

        return rooms

