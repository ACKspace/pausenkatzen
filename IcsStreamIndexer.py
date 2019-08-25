from icalendar import Calendar, Event
import requests
import threading
import datetime
from dateutil.parser import parse
from dateutil.tz import tzoffset

class IcsStreamIndexer:
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
        self.schedule = Calendar.from_ical(response.text)
        #print( self.schedule )

    def getStreamLocations(self):
        locations = set()
        if ( self.schedule ):
            for event in self.schedule.walk('vevent'):
                location = str(event['location'])
                if ( location ):
                    locations.add( str(event['location']) )
        return list( locations )

    def getActiveStreams(self,timestamp=datetime.datetime.now(tzoffset('UTC+2', 2*3600))):
        if ( not self.schedule ):
            return {}

        locations = {}

        # Distill active talks
        for event in self.schedule.walk('vevent'):
            start = event.get('dtstart').dt - self.margin
            end = event.get('dtend').dt + self.margin + self.margin
            location = str(event['location'])

            # TODO: process description as stream uri
            #description = str(event['description']) # HTML
         
            #print( description )
            if ( timestamp > start and timestamp < end ):
                locations[ location ] = event['summary']
        return locations

