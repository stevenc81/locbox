"""
This is a code challenge for LocBox. It list out room availability in aspecified
city
"""
import sys, getopt
from datetime import datetime as DT
import datetime
import requests
import json
import pymongo

DT_FORMAT = "%m/%d/%Y"
QUERY_DAYS = 7

mongo = pymongo.MongoClient('localhost', 27017)
db = mongo['airbnb']

class Room(object):
    """
    Room holds essential attributes for a room. Upon instantiation a new
    entry will be inserted to the database
    """

    def __init__(self, id_, name):
        super(Room, self).__init__()
        self.id_ = id_
        self.name = name
        self.available_dates = []
        db.rooms.save(self.db__repr__())

    def add_available_date(self, date):
        self.available_dates.append(date)

        # Appearenr MongoDB doesn't conver datetime.date naturally. It has to be
        # converted to datetime.datetime
        db.rooms.update(
                {'_id': self.id_},
                {'$addToSet': {
                        'available_dates': DT(date.year, date.month, date.day)
                    }
                }
            )

    def __str__(self):
        return (u"Room ID: %s \nRoom Name: %s \nAvailability: %s" % \
               (self.id_, self.name, self.avail)).encode('utf-8')

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def db__repr__(self):
        return {
                '_id': self.id_,
                'name': self.name,
                'available_dates': self.available_dates
                }

def query_db(start_date, end_date):
    """
    Query DB for room availability in between 2 sepcified query_dates
    """

    query_dates = [start_date + datetime.timedelta(days=x) \
                  for x in range((end_date - start_date).days + 1)]

    rv = db.rooms.find({
        'available_dates': {
            '$all': query_dates
        }
        })

    print 'Rooms available from %s to %s' % (start_date.strftime(DT_FORMAT), \
           end_date.strftime(DT_FORMAT))

    for room in rv:
        print 'Name: %s, ID: %s' % (room['name'], room['_id'])

def teardown():
    """
    Deletes every record created in the database
    """

    rv = db.rooms.remove()
    print 'Teardown: %s records in DB are removed' % rv['n']

def get_airbnb_data(city):
    """
    Gets room availability for a specified city from the next 7 days
    """

    today_date = DT.utcnow().date()
    query_dates = [(today_date + datetime.timedelta(days=x)) \
                  for x in range(QUERY_DAYS)]

    prop_dict = {}
    for checkin_date in query_dates:
        checkout_date = checkin_date + datetime.timedelta(days=1)

        http_url = 'https://www.airbnb.com/search/ajax_get_results?location=' + \
                    city + '&checkin=' + checkin_date.strftime(DT_FORMAT) + \
                    '&checkout=' + checkout_date.strftime(DT_FORMAT)

        print "Getting available properties with query: ",
        print http_url

        results = requests.get(http_url)
        json_result = json.loads(results.text)

        print "%d results are returned" % len(json_result['properties'])

        for prop in json_result['properties']:
            prop_id = prop.get('id')
            prop_name = prop.get('name')

            if prop_id not in prop_dict:
                prop_dict[prop_id] = Room(prop_id, prop_name)
                prop_dict[prop_id].add_available_date(checkin_date)
            else:
                prop_dict[prop_id].add_available_date(checkin_date)

    print "%s of unique properties retrieved" % len(prop_dict)

    prop_names = [v.name for k, v in prop_dict.iteritems()]
    max_len = len(max(prop_names, key=len))

    space = 7
    print '-' * ((space + 1) * QUERY_DAYS + max_len)
    print '|' + ' ' * max_len + '|',

    print '|'.join(date.strftime('%m/%d').center(space) for date in query_dates)

    print '-' * ((space + 1) * QUERY_DAYS + max_len)

    for id_, prop in prop_dict.iteritems():
        print '|' + prop.name.center(max_len) + '|',

        for date in query_dates:
            if date in prop.available_dates:
                print ''.center(space),
            else:
                print 'x'.center(space),
        print


def main():
    """
    Usage:

    -s, `start date`
    -e, `end date`
    single arg `city name`

    if -s or -e is omitted the program will assume a 7 days duration. Date is in
    UTC and have to be complete.

    Example:

        -s 08/04/2013 -e 08/07/2013 SF
    """

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:e:', ['help'])
    except getopt.error, msg:
        print msg
        print "for help use --help"
        sys.exit(2)

    start_date = end_date = None
    for o, a in opts:
        if o in ('-h', '--help'):
            print main.__doc__
            sys.exit(0)
        elif o == '-s':
            try:
                start_date = DT.strptime(a, DT_FORMAT)
            except ValueError:
                print "Bad date format"
                sys.exit(2)
        elif o == '-e':
            try:
                end_date = DT.strptime(a, DT_FORMAT)
            except ValueError:
                print "Bad date format"
                sys.exit(2)

    if end_date < start_date:
        print "End date cannot be bigger than start date"
        sys.exit(2)

    if start_date is None or end_date is None:
        start_date = DT.utcnow().date()
        start_date = DT(start_date.year, start_date.month, start_date.day)

        end_date = (start_date + datetime.timedelta(days=QUERY_DAYS))
        end_date = DT(end_date.year, end_date.month, end_date.day)

    city = None
    if len(args) > 0:
        city = args[0]
    else:
        print "Missing argument"
        print "for help use --help"
        sys.exit(2)

    print "Getting room availability for city of %s from %s to %s" % \
          (city, start_date.strftime(DT_FORMAT), end_date.strftime(DT_FORMAT))

    get_airbnb_data(city)
    query_db(start_date=start_date, end_date=end_date)
    teardown()

if __name__ == '__main__':
    main()
