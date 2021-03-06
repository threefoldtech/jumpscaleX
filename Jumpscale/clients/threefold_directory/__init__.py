# DO NOT EDIT THIS FILE. This file will be overwritten when re-running go-raml.

from .ActualUsedCapacity import ActualUsedCapacity
from .Capacity import Capacity
from .Error import Error
from .Farmer import Farmer
from .Location import Location
from .ReservedCapacity import ReservedCapacity
from .ResourceUnits import ResourceUnits

from .api_service import ApiService

from .http_client import HTTPClient


class Client:
    def __init__(self, base_uri=""):
        http_client = HTTPClient(base_uri)
        self.api = ApiService(http_client)
        self.close = http_client.close
