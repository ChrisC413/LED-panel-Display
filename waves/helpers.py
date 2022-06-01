import adafruit_requests as requests

def split_date(prediction):
    prediction['h'] , prediction['m'] = prediction['t'].split(" ", 2)[1].split(":")
    return prediction

def generate_noaa_url(station):
    """Build and return the URL for the tides API."""
    URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?format=json"
    URL += "&product=predictions"
    URL += "&interval=hilo"
    URL += "&datum=mllw"  # MLLW = "tides"
    URL += "&units=metric"
    URL += "&time_zone=lst_ldt"
    URL += "&date=today"
    URL += "&station=" + station
    return URL

def get_tide_data(station):
    """Fetch JSON tide data and return parsed results in a list."""
    # Get raw JSON data
    response = requests.get(generate_noaa_url(station))
    response = response.json()
    response = map(split_date, response['predictions'])
    return list(response)

def calculate_nearest_tides(station, time):
    predictions = get_tide_data(station)
    curr_hour = getattr(time.localtime(), 'tm_hour')
    curr_min = getattr(time.localtime(), 'tm_min')
    nearest = {}
    for i, prediction in enumerate(predictions):
        if int(prediction['h']) <= curr_hour:
            nearest['previous'] = prediction
            print(f'parse index: {i}')
            if len(predictions) > i+1:
                nearest['next'] = predictions[i+1]
            else:
                nearest['next'] = {'h': str((int(prediction['h']) + 6) % 24),
                                   'm': prediction['m'],
                                   'type': 'L' if prediction['type'] == 'H' else 'H'}
    if 'previous' not in nearest:
        nearest['next'] = predictions[0]
        nearest['previous'] = {'h': str(24 - int(nearest['next']['h'])) ,
                               'm': nearest['next']['m'],
                               'type': 'L' if nearest['next']['type'] == 'H' else 'H'}
    nearest['direction'] = 'in' if nearest['previous']['type'] == 'L' else 'out'

    # how close to the next tide are we?
    next_tide = int(nearest['next']['h'])
    if next_tide < curr_hour:
        next_tide = next_tide + 24

    mins_till_next_tide = (next_tide - curr_hour) * 60 \
        + int(nearest['next']['m']) - curr_min

    nearest['interval'] = mins_till_next_tide
    return nearest
