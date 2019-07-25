from enum import Enum

class UnitType(Enum):
    METRIC = 1
    IMPERIAL = 2

class FractionalPlates(Enum):
    TWONHALF: 1
#Unit type
WEIGHT_UNIT_TYPE = UnitType.METRIC
DISTANCE_UNIT_TYPE = UnitType.METRIC

#Smallest Fractional Plates
FRACTIONAL_PLATES = FractionalPlates.TWONHALF

#Rounding

ROUNDING = False
