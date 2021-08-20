import json
import numpy as np
from shapely import geometry

from database import db
from support.serializer import Serializer
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from support.point import Point as pt

def to_json(inst, cls):
    """
    Jsonify the sql alchemy query result.
    """
    convert = dict()
    # add your coversions for things like datetime's
    # and what-not that aren't serializable.
    d = dict()
    for c in cls.__table__.columns:
        v = getattr(inst, c.name)
        if c.type in convert.keys() and v is not None:
            try:
                d[c.name] = convert[c.type](v)
            except:
                d[c.name] = "Error:  Failed to covert using ", str(convert[c.type])
        elif v is None:
            d[c.name] = str()
        else:
            d[c.name] = v
    return json.dumps(d)


class Trip(db.Model):
    __tablename__ = 'trips'
    trip_id = db.Column(db.Integer, primary_key=True)
    origin_latitude = db.Column(db.String(250))
    origin_longitude = db.Column(db.String(250))
    destination_latitude = db.Column(db.String(250))
    destination_longitude = db.Column(db.String(250))
    date = db.Column(db.DateTime)
    datasource_id = db.Column(db.Integer, db.ForeignKey('datasources.datasource_id'))
    region_id = db.Column(db.Integer, db.ForeignKey('regions.region_id'))


    @classmethod
    def get_all(cls):
        return Trip.query.all()

    def serialize(self):
        serialized_trip = Serializer.serialize(self)
        return serialized_trip

    def is_inside(self,polygon_points):
        origin_point = Point(float(self.origin_latitude), float(self.origin_longitude))
        destination_point = Point(float(self.destination_latitude), float(self.destination_longitude))

        point_list = []
        for point in polygon_points:
            new_pt = pt(point)
            new_point = Point(float(new_pt.latitude), float(new_pt.longitude))
            point_list.append(new_point)

        polygon = geometry.Polygon([[p.y, p.x] for p in point_list])
        return polygon.contains(origin_point) & polygon.contains(destination_point)

    @property
    def json(self):
        return to_json(self, self.__class__)


class SimilarTrips(db.Model):
    __tablename__ = 'similar_trips'
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.trip_id'))
    similar_trip_id = db.Column(db.Integer, db.ForeignKey('trips.trip_id'))


class Region(db.Model):
    __tablename__ = 'regions'
    region_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250))
    regions = db.relationship('Trip',backref='trips')

    @classmethod
    def find_by_name(cls, name):
        region = Region.query.filter_by(name=name).first()
        return region.region_id

    @classmethod
    def find_trips(cls, name):
        regions = Region.query.filter_by(name=name).first().regions
        return regions

    def serialize(self):
        serialized_region = Serializer.serialize(self)
        return serialized_region

    @property
    def json(self):
        return to_json(self, self.__class__)


class Datasource(db.Model):
    __tablename__ = 'datasources'
    datasource_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250))

    @classmethod
    def find_by_name(cls, name):
        datasource = Datasource.query.filter_by(name=name).first()
        return datasource.datasource_id

    def serialize(self):
        serialized_ds = Serializer.serialize(self)
        return serialized_ds