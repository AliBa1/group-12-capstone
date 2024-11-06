folder_path = "./"
file_name = "singlefamilyhome_time_city.csv"

import pandas

home_data_city_time = pandas.read_csv("singlefamilyhome_time_city.csv")

print(home_data_city_time)


# Features
# RegionID,SizeRank,RegionName,RegionType,StateName,State,Metro,CountyName
# Target
# 2000-01-31,2000-02-29,2000-03-31,2000-04-30,2000-05-31,2000-06-30,2000-07-31,2000-08-31, ...

#features = []
#target = []
#X = home_data_city_time[]