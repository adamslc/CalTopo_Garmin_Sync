import logging
import time
import requests
import xml.etree.ElementTree as ET

class Tracker:
    def __init__(self, group, id):
        self.group = group
        self.id = id
        self.last_coords = {'lat': None, 'lng': None}
        self.coord_update_time = None
        self.coord_send_time = None

    def post_coords(self):
        logging.info(f'Posting coordinates to CalTopo for {self.group}-{self.id}')
        if self.coord_update_time == None:
            logging.warning('Coordinates have not been initalized. Aborting.')
            return

        if (not self.coord_send_time == None) and (self.coord_send_time > self.coord_update_time):
            logging.info('Coordinates have not been updated since last send. Aborting.')
            return

        resp = requests.get(
            f'https://caltopo.com/api/v1/position/report/{self.group}?id={self.id}',
            params=self.last_coords
        )
        self.coord_send_time = time.time()

        if not resp.status_code == 200:
            logging.warning('CalTopo returned status code {resp.status_code}.')


class GarminTracker(Tracker):
    def __init__(self, group, id, name, mapshare_code):
        super().__init__(group, id)
        self.name = name
        self.mapshare_code = mapshare_code

    def _namespace_tag(self, tag):
        return '{http://www.opengis.net/kml/2.2}' + tag

    def _parse_garmin_coords(self, kml_str):
        root = ET.fromstring(kml_str)

        doc = root.find(self._namespace_tag('Document'))
        folder = doc.find(self._namespace_tag('Folder'))
        placemark = folder.find(self._namespace_tag('Placemark'))
        point = placemark.find(self._namespace_tag('Point'))
        coords_str = point.find(self._namespace_tag('coordinates')).text

        lng, lat, elv = coords_str.split(',')
        return {'lat': lat, 'lng': lng}

    def update_coords(self):
        logging.info(f'Getting Garmin coordinates for MapShare code {self.mapshare_code}')
        resp = requests.get(f'https://inreach.garmin.com/feed/share/{self.mapshare_code}')
        try:
            new_coords = self._parse_garmin_coords(resp.text)
            if not new_coords == self.last_coords:
                logging.info('Updating coordinates.')
                self.last_coords = new_coords
                self.coord_update_time = time.time()
            else:
                logging.info('Coordinates have not changed since last request. Skipping update.')
        except:
            logging.error('Parsing of kml file failed. Coordinates not updated.')


def main():
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)

    logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")

    fileHandler = logging.FileHandler('server.log')
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    trackers = [
        GarminTracker('LCASJS', 'Amanda', 'Amanda Mercer', 'ZVV23'),
    ]

    while True:
        logging.info('Starting location updates...')
        for tracker in trackers:
            logging.info(f'Updating location for {tracker.name}')
            tracker.update_coords()
            tracker.post_coords()
        logging.info('Finished updating location. Sleeping...')
        time.sleep(60)


main()
