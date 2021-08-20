import io
import json

import flask
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_restful import Resource, Api, reqparse
import csv
from datetime import datetime
from database import db
from models.trip import Trip, SimilarTrips, Region, Datasource
from support.haversine import Haversine
from support.point import Point
from support.serializer import Serializer

app = Flask(__name__)
app.config.from_object('config')
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('list', type=list)

# init db instance
db.init_app(app)

# config flask migrate
migrate = Migrate()
migrate.init_app(app, db)


class Trips(Resource):
    # parameter to define the distance between trips in order to consider them similar. Represents kilometers(km)
    _PARAM_SIMILARITY = 1000

    @classmethod
    def set_up(cls):
        SimilarTrips.query.delete()
        Trip.query.delete()
        Datasource.query.delete()
        Region.query.delete()

    def get(self):
        regions = Region.query.all()
        trips = Trip.query.all()
        print(regions)
        count_trips = Trip.query.count()
        return json.dumps(Serializer.serialize_list(regions))

    # method to process the csv datafile
    def post(self):

        # delete the data from all tables
        Trips.set_up()

        # read csv file sent
        file = request.files['file']
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)

        # convert csv file in list
        trips_list = list(csv_input)

        # Load Regions and Datasources from the csv file list
        Trips.load_datasources_regions(trips_list)

        '''
        Creates a dictionary : key (hour and minute) : values = [Trip,..] to group trips with the same hour and minute.
        Also inserts all Trips in the database
        '''
        diccionary = Trips.process_trip_list(trips_list)

        '''
        With Haversine's algorithm, the dictionary is read by taking each key from the dictionary and the trips for 
        each key, and with that the distance between each trip is calculated. Then those with distance less than 
        _PARAM_SIMILARITY are assigned as similar trips. 
        '''
        Trips.process_similarity(diccionary, Trips._PARAM_SIMILARITY)

        return {'results': 'ok'}

    @classmethod
    def load_datasources_regions(cls, trips):
        first_row = True
        datasource = []
        region = []
        for row in trips:
            if first_row:
                first_row = False
            else:
                datasource.append(row[4])
                region.append(row[0])
        region_set = set(region)
        datasource_set = set(datasource)

        reg_insert = []
        for region in region_set:
            reg = Region(name=region)
            reg_insert.append(reg)
        db.session.add_all(reg_insert)
        db.session.commit()

        datasource_insert = []
        for datasource in datasource_set:
            ds = Datasource(name=datasource)
            datasource_insert.append(ds)
        db.session.add_all(datasource_insert)
        db.session.commit()

    @classmethod
    def process_trip_list(cls, trips_list):
        first_row = True
        dictionary = {}
        for trip_csv in trips_list:

            if first_row:
                first_row = False
            else:
                date = datetime.strptime(str(trip_csv[3]).strip(), '%Y-%m-%d %H:%M:%S')
                hour_minute = str(date.hour) + ':' + str(date.minute)

                trip = Trip(region_id=Region.find_by_name(trip_csv[0]), origin_latitude=Point(trip_csv[1]).latitude,
                            origin_longitude=Point(trip_csv[1]).longitude,
                            destination_latitude=Point(trip_csv[2]).latitude,
                            destination_longitude=Point(trip_csv[2]).longitude, date=date,
                            datasource_id=Datasource.find_by_name(trip_csv[4]))
                db.session.add(trip)
                db.session.commit()
                if hour_minute in dictionary:
                    dictionary[hour_minute].append(trip)
                else:
                    dictionary[hour_minute] = [trip]

        return dictionary

    @classmethod
    def process_similarity(cls, dictionary, param_similarity):
        for key in dictionary:
            lista_values = dictionary[key]
            for trip in lista_values:
                similar_origin = list(filter(
                    lambda c: Haversine.calculate_distance(float(c.origin_latitude), float(c.origin_longitude),
                                                           float(lista_values[0].origin_latitude),
                                                           float(lista_values[0].origin_longitude)) <= param_similarity,
                    lista_values))
                similar_destination = list(filter(
                    lambda c: Haversine.calculate_distance(float(c.destination_latitude),
                                                           float(c.destination_longitude),
                                                           float(similar_origin[0].destination_latitude),
                                                           float(similar_origin[
                                                                     0].destination_longitude)) <= param_similarity,
                    similar_origin))

                for sim in similar_destination:
                    if sim.trip_id != trip.trip_id:
                        similar_trip = SimilarTrips(trip_id=trip.trip_id, similar_trip_id=sim.trip_id)
                        db.session.add(similar_trip)
                        db.session.commit()


class TripList(Resource):

    '''
    Method that expects a json with two different attributes:
        list : with a list of points to find trips inside that list
        region : with a name of a region to find trips for that region
    '''
    def get(self):
        not_point_list = False
        not_region = False

        dic = request.json
        try:
            points = dic['list']
        except Exception as e:
            points = None
            not_point_list = True

        try:
            region = dic['region']
        except Exception as e:
            region = None
            not_region = True


        if not_region & not_point_list:
            return jsonify('{ "Result": "Did not send properties list or region"}')


        if not not_point_list:
            print(points)
        if not not_region:
            print(region)

        TripList.search_by_points_or_region(points, region)

        return jsonify('{ "Result": "OK"}')

    @classmethod
    def search_by_points_or_region(cls, points, region):
        trips_inside = []
        if region:
            region_trips = Region.find_trips(region)
            trips = region_trips
        else:
            trips = Trip.get_all()

        for trip in trips:
            if trip.is_inside(points):
                trips_inside.append(trip)


        # if points:
        #
        #     trips =
        #
        #
        # TripList.calculate_weekly_average(trips)






api.add_resource(Trips, '/trips')
api.add_resource(TripList, '/tripList')

if __name__ == '__main__':
    app.run(debug=True)
