from numpy import array, meshgrid, nan, percentile
from pandas import DataFrame, pivot_table
from pymongo.mongo_client import MongoClient
from h3 import geo_to_h3, h3_to_geo, edge_length
import pickle
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, PULP_CBC_CMD
from folium import plugins, Map, CircleMarker, Marker, Icon


from optimal_loc.app_constants import (
    HEX_LAT, FROMHEX, TOHEX, HEX_LOCATION, SUPPLY_HEXAGON_ID, TOTAL_EVENT, HEX_ID, HEX_LON, HEXAGON_ID, LATITUDE,
    LONGITUDE, FROMHEX_LAT, FROMHEX_LON, HEXAGON, FILENAME, DISTANCE, SUPPLY_DATA_COLUMN, OPTIMAL_DATA_COLUMN, INDEX
)


def set_resolution(raw_data: DataFrame, hex_size: str):
    if hex_size == 'medium':
        resolution = 8
    elif hex_size == 'big':
        resolution = 5
    elif hex_size == 'small':
        resolution = 10
    else:
        resolution_set = 0
        resolution = 15
        while resolution_set == 0:
            if raw_data.apply(lambda x: geo_to_h3(x[LATITUDE], x[LONGITUDE], resolution), 1).nunique() < 150:
                resolution_set = 1
            else:
                resolution = resolution - 1
    return resolution


class OptimalLoc:
    def __init__(self):
        self.supply_data = None
        self.optimal_data = None
        self.hex_distance_data = None
        self.event_frequency_data = None
        self.resolution = None

    def plot_frequency_hexagons(self):
        plot_data = self.event_frequency_data.copy()
        perc_90 = percentile(plot_data["total_event"], 90)
        perc_75 = percentile(plot_data["total_event"], 75)
        plot_data["colors"] = plot_data["total_event"].apply(lambda x: "red" if x > perc_90 else (
            "green" if x > perc_75 else "blue"), 1)
        WHS_COORD = [plot_data['hex_lat'].median(), plot_data['hex_lon'].median()]
        map_nyc = Map(location=WHS_COORD, zoom_start=10, width=740, height=500)

        for j, i in plot_data.iterrows():
            CircleMarker((i["hex_lat"], i["hex_lon"]),
                         radius=5, color=i["colors"],
                         popup={"Total Event": i["total_event"]}
                         ).add_to(map_nyc)

        plugins.Fullscreen(position='topleft').add_to(map_nyc)

        return map_nyc

    def event_frequency(self, raw_input_data: DataFrame, hex_size: str = 'auto') -> None:
        """
        Calculate the frequency of events in each hexagonal region.

        Parameters:
        raw_data (DataFrame): pandas DataFrame containing event data, with columns "latitude" and "longitude".
        hex_size (string): You can specify hexagon sizes by small, medium or big, otherwise it will be assigned as auto

        Returns:
        None

        Description:
        This function calculates the frequency of events in each hexagonal region based on the provided event data.
        It utilizes the H3 library to convert latitude and longitude coordinates to hexagonal IDs.
        The function updates the 'event_frequency_data' attribute with the resulting DataFrame, which contains
        the hexagonal region IDs, total event counts, and corresponding latitude and longitude coordinates.

        Note:
        This function assumes that the 'geo_to_h3' and 'h3_to_geo' functions from the H3 library are available.

        Example:
        raw_event_data = pd.DataFrame({'latitude': [42.123, 42.456, 42.789], 'longitude': [-71.123, -71.456, -71.789]})
        object_name = OptimalLoc()
        object_name.event_frequency(raw_event_data)
        event_freq_data = object_name.event_frequency_data
        print(event_freq_data)
        """
        raw_data = raw_input_data.copy()
        self.resolution = set_resolution(raw_data, hex_size)

        raw_data[HEX_ID] = raw_data.apply(lambda x: geo_to_h3(x[LATITUDE], x[LONGITUDE], self.resolution), 1)

        raw_data = raw_data[HEX_ID].value_counts().reset_index().rename(columns={INDEX: HEXAGON_ID,
                                                                                 HEX_ID: TOTAL_EVENT})
        raw_data[HEX_LOCATION] = raw_data.apply(lambda x: h3_to_geo(h=x[HEXAGON_ID]), 1)
        raw_data[HEX_LAT] = raw_data.apply(lambda x: x[HEX_LOCATION][0], 1)
        raw_data[HEX_LON] = raw_data.apply(lambda x: x[HEX_LOCATION][1], 1)
        raw_data = raw_data.drop(columns=HEX_LOCATION)

        self.event_frequency_data = raw_data

    def create_hexagon_distance_data(self, raw_data: DataFrame, hex_size: str = 'auto') -> None:
        """
        Create a DataFrame containing the distances between pairs of hexagonal regions.

        Parameters:
        raw_data (DataFrame): pandas DataFrame containing event data, with columns "latitude" and "longitude".
        hex_size (string): You can specify hexagon sizes by small, medium or big, otherwise it will be assigned as auto

        Returns:
        DataFrame: A pandas DataFrame containing columns "fromhex", "tohex", "fromhex_lat", "fromhex_lon", "tohex_lat", "tohex_lon", and "distance".

        Description:
        This function creates a DataFrame that represents the distances between pairs of hexagonal regions.
        It first calculates the event frequency using the 'event_frequency' function and then generates a meshgrid of hexagon IDs.
        The resulting DataFrame includes columns that represent the source hexagon, target hexagon, and their corresponding latitude and longitude coordinates.
        The distance between each pair of hexagons is not calculated in this function.

        Note:
        This function assumes that the 'event_frequency' function has been executed to generate the 'event_frequency_data' attribute.
        The meshgrid and array functions are imported from numpy.
        You can calculate yourself the real distances after this function completed.

        Example:
        raw_event_data = pd.DataFrame({'latitude': [42.123, 42.456, 42.789], 'longitude': [-71.123, -71.456, -71.789]})
        object = OptimalLoc()
        object.create_hexagon_distance_data(raw_event_data)
        hex_distance_data = object.hex_distance_data
        """
        self.event_frequency(raw_data, hex_size)
        event_data = self.event_frequency_data.copy()

        hexagon_ids = event_data[[HEXAGON_ID, HEX_LAT, HEX_LON]].rename(columns={HEXAGON_ID: HEXAGON})
        out_list = array(meshgrid(hexagon_ids.hexagon, hexagon_ids.hexagon)).T.reshape(-1, 2)

        hex_distance_data = DataFrame(data=out_list, columns=[FROMHEX, TOHEX])

        hex_distance_data = hex_distance_data.merge(
            hexagon_ids[[HEXAGON, HEX_LAT, HEX_LON]].rename(
                columns={HEX_LON: FROMHEX_LON, HEX_LAT: FROMHEX_LAT}),
            left_on=FROMHEX,
            right_on=HEXAGON,
            how="left").drop(columns=[HEXAGON])

        hex_distance_data = hex_distance_data.merge(
            hexagon_ids[[HEXAGON, HEX_LAT, HEX_LON]],
            left_on=TOHEX,
            right_on=HEXAGON,
            how="left").drop(columns=[HEXAGON]).rename(columns={HEX_LON: "tohex_lon", HEX_LAT: 'tohex_lat'})

        # Average distance between two random points within a circle according to its diameter = (2 * radius) / 3
        eq_hex_distance = int((edge_length(self.resolution, "m") * 2) / 3)
        hex_distance_data[DISTANCE] = hex_distance_data.apply(lambda x: eq_hex_distance if x[FROMHEX] == x[TOHEX] else nan, 1)

        self.hex_distance_data = hex_distance_data

        print("Distance data for each hexagons was created. You can read it by object_name.hex_distance_data")

    def read_distances_from_mongodb(self, mongo_client: MongoClient,
                                    mongo_database_name: str,
                                    mongo_collection_name: str):
        """
        Reads distance data from a MongoDB collection and stores it in a DataFrame.

        Parameters:
            mongo_client (MongoClient): The MongoDB client object used to connect to the MongoDB server.
            mongo_database_name (str): The name of the MongoDB database containing the distance data.
            mongo_collection_name (str): The name of the MongoDB collection containing the distance data.

        Raises:
            ConnectionError: If there is an error connecting to the MongoDB server.

        Returns:
            None

        Note:
            This function assumes that the MongoDB client has already been properly configured
            and connected to the server.

        Example:
            mongo_client = MongoClient('mongodb://localhost:27017')
            database_name = 'mydb'
            collection_name = 'distances'
            object = OptimalLoc()
            object.read_distances_from_mongodb(mongo_client, database_name, collection_name)
        """
        try:
            mongo_client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)
            raise ConnectionError()

        db = mongo_client[mongo_database_name]
        col = db[mongo_collection_name]
        distance_data = DataFrame(list(col.find()))
        # TODO: Write a exception for the column names

        self.hex_distance_data = distance_data

    def read_distances(self, read_from_dataframe: bool = False,
                       read_from_mongo: bool = False,
                       distance_dataframe: DataFrame = DataFrame(),
                       mongo_client: MongoClient = None,
                       mongo_database_name: str = None,
                       mongo_collection_name: str = None):

        """
        Reads distance data from a specified source and stores it in the `hex_distance_data` attribute.

        Parameters:
            read_from_dataframe (bool): Flag indicating whether to read distance data from a DataFrame. Default is False.
            read_from_mongo (bool): Flag indicating whether to read distance data from a MongoDB collection. Default is False.
            distance_dataframe (DataFrame): A pandas DataFrame containing the distance data. Default is an empty DataFrame.
            mongo_client (MongoClient): The MongoDB client object used to connect to the MongoDB server. Default is None.
            mongo_database_name (str): The name of the MongoDB database containing the distance data. Default is None.
            mongo_collection_name (str): The name of the MongoDB collection containing the distance data. Default is None.

        Raises:
            ValueError: If both `read_from_dataframe` and `read_from_mongo` are True or if none of them are True.
            ValueError: If `read_from_dataframe` is True but `distance_dataframe` is an empty DataFrame.
            ValueError: If `read_from_mongo` is True but any of `mongo_client`, `mongo_database_name`, or `mongo_collection_name` is None.

        Returns:
            None

        Note:
            This function requires either `read_from_dataframe` or `read_from_mongo` to be True in order to read the distance data.
            If reading from a DataFrame, the `distance_dataframe` parameter must contain the distance data with specific column names.
            If reading from a MongoDB collection, the `mongo_client`, `mongo_database_name`, and `mongo_collection_name` parameters must be provided.

        Example:
            # Read distance data from a DataFrame
            distance_df = pd.read_csv('distance_data.csv')
            object = OptimalLoc()
            object.read_distances(read_from_dataframe=True, distance_dataframe=distance_df)

            # Read distance data from a MongoDB collection
            mongo_client = MongoClient('mongodb://localhost:27017')
            database_name = 'mydb'
            collection_name = 'distances'
            object = OptimalLoc()
            object.read_distances(read_from_mongo=True, mongo_client=mongo_client,
                                  mongo_database_name=database_name, mongo_collection_name=collection_name)
        """

        # raise an error if more than one input is True
        if sum([read_from_dataframe, read_from_mongo]) > 1:
            raise ValueError("You can read the distance from only one source.")

        if sum([read_from_dataframe, read_from_mongo]) == 0:
            raise ValueError("You need to specify at least one data source to read the real hexagon distances.")

        # otherwise, do something with the input that is True
        if read_from_dataframe:
            if len(distance_dataframe) == 0:
                raise ValueError("""
                distance_dataframe:pandas.DataFrame can not be null if you want to read distances from a data frame.
                Please give the distance data as a dataframe where columns should be 
                'fromhex', 'tohex', 'fromhex_lat', 'fromhex_lon', 'tohex_lat', 'tohex_lon', 'distance'
                """)

            self.hex_distance_data = distance_dataframe
            print("Successfully read the distance data")

        elif read_from_mongo:
            if mongo_client and mongo_database_name and mongo_collection_name:
                self.read_distances_from_mongodb(
                    mongo_client=mongo_client,
                    mongo_database_name=mongo_database_name,
                    mongo_collection_name=mongo_collection_name)
                print("Successfully read the distance data")

            else:
                raise ValueError("""
                mongo_client:MongoClient,
                mongo_database_name:str
                mongo_collection_name:str features can not be null if you want to read distances from a MongoDb.
                """)

        else:
            # do something with c
            pass

    def prepare_data_tables(self, pulp_solution, frequency_data: DataFrame):
        """
        Prepares data tables for analysis based on the solution obtained from a Pulp optimization model and frequency data.

        Parameters:
            pulp_solution: The solution obtained from a Pulp optimization model.
            frequency_data (DataFrame): A pandas DataFrame containing frequency data.

        Returns:
            dict: A dictionary containing the analysis results with the following keys:
                - "optimal_data": DataFrame containing the optimal assignment of supply and hexagon IDs.
                - "supply_data": DataFrame containing the supply data for the assigned hexagons.

        Note:
            This function assumes that the solution provided is compatible with the frequency data.

        """
        analysis_result = {}

        wh_loc = []
        hex_loc = []
        assign = []
        for v in pulp_solution.variables()[len(frequency_data):]:
            wh_loc.append(v.name.split("_")[1])
            hex_loc.append(v.name.split("_")[2])
            assign.append(v.varValue)
        df = DataFrame({SUPPLY_HEXAGON_ID: wh_loc, HEXAGON_ID: hex_loc, "assign": assign})
        optimal_data = df[df["assign"] != 0].reset_index(drop=True)

        optimal_data = optimal_data.merge(
            frequency_data[[HEXAGON_ID, HEX_LAT, HEX_LON]],
            on=HEXAGON_ID,
            how="left").drop(columns=["assign"])

        supply_data = frequency_data[frequency_data[HEXAGON_ID].isin(
            list(optimal_data[SUPPLY_HEXAGON_ID].unique()))].reset_index(drop=True).rename(
            columns={HEXAGON_ID: SUPPLY_HEXAGON_ID})
        
        self.optimal_data = optimal_data
        self.supply_data = supply_data
        
        analysis_result[OPTIMAL_DATA_COLUMN] = optimal_data.to_dict()
        analysis_result[SUPPLY_DATA_COLUMN] = supply_data.to_dict()

        return analysis_result

    def calculate_optimal_locations(self, number_of_loc: int,
                                    distance_data: DataFrame = None,
                                    frequency_data: DataFrame = None
                                    ):
        """
        Calculates the optimal locations based on the given number of locations and distance/frequency data.

        Parameters:
            number_of_loc (int): The number of optimal locations to calculate.
            distance_data (DataFrame): A pandas DataFrame containing distance data. Default is None.
            frequency_data (DataFrame): A pandas DataFrame containing frequency data. Default is None.

        Raises:
            ValueError: If `distance_data` or `frequency_data` is None or not provided.

        Returns:
            None

        Note:
            This function assumes that the necessary data has been provided either through the function parameters or through previous function calls.

        Example:
            object = OptimalLoc()
            object.calculate_optimal_locations(number_of_loc=3, distance_data=distances_df, frequency_data=frequency_df)
        """

        if distance_data is None:
            distance_data = self.hex_distance_data
        if frequency_data is None:
            frequency_data = self.event_frequency_data
        if distance_data is None or frequency_data is None:
            raise ValueError("""
                Please specify distance_data and frequency_data or run related functions.
            """)

        distance_matrix = pivot_table(
            distance_data, 
            values=DISTANCE,
            index=FROMHEX,
            columns=TOHEX
        )
        
        distance_matrix.columns.name = None
        distance_matrix.index.name = None

        event_matrix = frequency_data[[HEXAGON_ID, TOTAL_EVENT]].set_index(HEXAGON_ID)
        event_matrix.index.name = None
        event_matrix = event_matrix.to_dict(INDEX)

        supplies = distance_data.fromhex.unique().tolist()
        demands = distance_data.fromhex.unique().tolist()
        distance = distance_matrix.to_dict(INDEX)

        prob = LpProblem("Transportation", LpMinimize)
        routes = [(i, j) for i in supplies for j in demands]

        # DECISION VARIABLES
        amount_vars = LpVariable.dicts("X", (supplies, demands), lowBound=0, upBound=1, cat='Binary')
        wh_vars = LpVariable.dicts("Supply", supplies, lowBound=0, upBound=1, cat='Binary')

        prob += lpSum(amount_vars[i][j] * distance[i][j] * event_matrix[j][TOTAL_EVENT] for (i, j) in routes)

        # CONSTRAINTS

        for j in demands:
            prob += lpSum(amount_vars[i][j] for i in supplies) == 1

        for i in demands:
            for j in supplies:
                prob += amount_vars[j][i] <= event_matrix[i][TOTAL_EVENT] * wh_vars[j]

        prob += lpSum(wh_vars[i] for i in supplies) == number_of_loc

        prob.solve(PULP_CBC_CMD(msg=0))

        results = self.prepare_data_tables(prob, frequency_data)

        with open(FILENAME, 'wb') as handle:
            pickle.dump(results, handle, protocol=pickle.HIGHEST_PROTOCOL)

        print(
            """
            You have successfully run the algorithm. To see the optimization results, you can run 
            object_name.supply_data or object_name.optimal_data 
            OR
            You can run optimal_loc.visualize() command to see the results on a map.
            """
        )
