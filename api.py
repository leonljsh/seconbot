import requests


class UglyKey:
    def __init__(self, key):
        self.keys = dict([[e.strip(' {}:"') for e in k.split('=>')] for k in key.split(',')])

    def get(self, key, default=None):
        return self.keys[key] if key in self.keys else default


class Api:
    def __init__(self, url):
        self.url = url
        self.rooms = dict(
            [(k, '#' + v.strip(' #')) for v, k in self._make_request(day=1).get("class_rooms_with_ids").items()])
        self.tracks = dict([(int(t['id']), t) for t in self.get_tracks(day=1)])

    def get_tracks(self, day=1):
        return self._make_request(day=day).get("tracks")

    def get_track(self, id):
        return self.tracks[id]['name']

    def get_room(self, id):
        return self.rooms[id]

    def get_hours(self, day=1):
        schedule = self._get_schedule(day)

        return [UglyKey(k).get('time') for k in schedule.keys()]

    def get_schedule_by_hour(self, day, hour):
        schedule = dict([(UglyKey(k).get('time'), v) for k, v in self._get_schedule(day).items()])

        return schedule.get(hour)

    def get_schedule_by_track(self, track_id, day):
        schedule = dict([(UglyKey(k).get('time'), v) for k, v in self._get_schedule(day).items()])

        result = []

        for time, item in schedule.items():
            if isinstance(item, list):
                for timeslot in item:
                    if track_id == timeslot.get('report', {}).get('track', {}).get('id'):
                        result.append({**timeslot, **{'time': time}})
            else:
                if track_id == item.get('report', {}).get('track', {}).get('id'):
                    result.append(result.append({**item, **{'time': time}}))

        return result


    def _get_schedule(self, day=1):
        return self._make_request(day=day).get("table")

    def _make_request(self, day):
        r = requests.get(self.url, params={'day': day})

        return r.json()
