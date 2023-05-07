import logging
from numpy import array, meshgrid
from pandas import DataFrame, pivot_table
from pymongo.mongo_client import MongoClient
from h3 import geo_to_h3, h3_to_geo
import pickle
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, PULP_CBC_CMD


class OptimalLoc:
    def __init__(self):
        self.supply_data = None
        self.optimal_data = None
        self.hex_distance_data = None
        self.event_frequency_data = None

    def event_frequency(self, raw_data: DataFrame) -> None:
        """
        Calculate the frequency of events in each hexagonal region.

        Parameters:
        event_data: pandas.DataFrame containing event data, with columns "latitude" and "longitude".

        Returns:
        None
        """
        raw_data["hex_id"] = raw_data.apply(lambda x: geo_to_h3(x["latitude"], x["longitude"], 8), 1)

        raw_data = raw_data['hex_id'].value_counts().reset_index().rename(columns={"index": "hexagon_id",
                                                                                   "hex_id": "total_event"})
        raw_data["hex_location"] = raw_data.apply(lambda x: h3_to_geo(h=x["hexagon_id"]), 1)
        raw_data["hex_lat"] = raw_data.apply(lambda x: x["hex_location"][0], 1)
        raw_data["hex_lon"] = raw_data.apply(lambda x: x["hex_location"][1], 1)
        raw_data = raw_data.drop(columns="hex_location")

        self.event_frequency_data = raw_data

    def create_hexagon_distance_data(self, raw_data: DataFrame) -> DataFrame:
        """
        Create a DataFrame containing the distances between pairs of hexagonal regions.

        Parameters:
        event_data: pandas.DataFrame containing event data, with columns "latitude" and "longitude".

        Returns:
        A pandas.DataFrame containing columns
        "fromhex", "tohex", "fromhex_lat", "fromhex_lon", "tohex_lat", "tohex_lon", and "distance".
        """
        self.event_frequency(raw_data)
        event_data = self.event_frequency_data

        hexagon_ids = event_data[["hexagon_id", "hex_lat", "hex_lon"]].rename(columns={"hexagon_id": "hexagon"})
        out_list = array(meshgrid(hexagon_ids.hexagon, hexagon_ids.hexagon)).T.reshape(-1, 2)

        hex_distance_data = DataFrame(data=out_list, columns=['fromhex', 'tohex'])

        hex_distance_data = hex_distance_data.merge(
            hexagon_ids[["hexagon", "hex_lat", "hex_lon"]].rename(
                columns={"hex_lon": "fromhex_lon", 'hex_lat': 'fromhex_lat'}),
            left_on="fromhex",
            right_on="hexagon",
            how="left").drop(columns=["hexagon"])

        hex_distance_data = hex_distance_data.merge(
            hexagon_ids[["hexagon", "hex_lat", "hex_lon"]],
            left_on="tohex",
            right_on="hexagon",
            how="left").drop(columns=["hexagon"]).rename(columns={"hex_lon": "tohex_lon", 'hex_lat': 'tohex_lat'})

        self.hex_distance_data = hex_distance_data

        logging.info(
            "Distance data for each hexagons was created. You can read it by object_name.hex_distance_data"
        )

        print("Distance data for each hexagons was created. You can read it by object_name.hex_distance_data")

    def read_distances_from_mongodb(self, mongo_client: MongoClient,
                                    mongo_database_name: str,
                                    mongo_collection_name: str):
        try:
            mongo_client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)
            raise ConnectionError()

        db = mongo_client[mongo_database_name]
        col = db[mongo_collection_name]
        distance_data = DataFrame(list(col.find()))
        self.hex_distance_data = distance_data

        return distance_data

    def read_distances(self, read_from_dataframe: bool = False,
                       read_from_mongo: bool = False,
                       distance_dataframe: DataFrame = DataFrame(),
                       mongo_client: MongoClient = None,
                       mongo_database_name: str = None,
                       mongo_collection_name: str = None):

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
            return distance_dataframe

        elif read_from_mongo:
            if mongo_client and mongo_database_name and mongo_collection_name:
                return self.read_distances_from_mongodb(
                    mongo_client=mongo_client,
                    mongo_database_name=mongo_database_name,
                    mongo_collection_name=mongo_collection_name)

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
        analysis_result = {}

        wh_loc = []
        hex_loc = []
        assign = []
        for v in pulp_solution.variables()[len(frequency_data):]:
            wh_loc.append(v.name.split("_")[1])
            hex_loc.append(v.name.split("_")[2])
            assign.append(v.varValue)
        df = DataFrame({"supply_hexagon_id": wh_loc, "hexagon_id": hex_loc, "assign": assign})
        optimal_data = df[df["assign"] != 0].reset_index(drop=True)

        optimal_data = optimal_data.merge(
            frequency_data[["hexagon_id", "hex_lat", "hex_lon"]],
            on="hexagon_id",
            how="left").drop(columns=["assign"])

        supply_data = frequency_data[frequency_data["hexagon_id"].isin(
            list(optimal_data["supply_hexagon_id"].unique()))].reset_index(drop=True).rename(
            columns={"hexagon_id": "supply_hexagon_id"})
        
        self.optimal_data = optimal_data
        self.supply_data = supply_data
        
        analysis_result["optimal_data"] = optimal_data.to_dict()
        analysis_result["supply_data"] = supply_data.to_dict()

        return analysis_result

    def calculate_optimal_locations(self, number_of_loc: int,
                                    distance_data: DataFrame = None,
                                    frequency_data: DataFrame = None
                                    ):

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
            values='distance',
            index="fromhex",
            columns="tohex"
        )
        
        distance_matrix.columns.name = None
        distance_matrix.index.name = None

        event_matrix = frequency_data[["hexagon_id", "total_event"]].set_index("hexagon_id")
        event_matrix.index.name = None
        event_matrix = event_matrix.to_dict('index')

        supplies = distance_data.fromhex.unique().tolist()
        demands = distance_data.fromhex.unique().tolist()
        distance = distance_matrix.to_dict('index')

        prob = LpProblem("Transportation", LpMinimize)
        routes = [(i, j) for i in supplies for j in demands]

        # DECISION VARIABLES
        amount_vars = LpVariable.dicts("X", (supplies, demands), lowBound=0, upBound=1, cat='Binary')
        wh_vars = LpVariable.dicts("Supply", supplies, lowBound=0, upBound=1, cat='Binary')

        prob += lpSum(amount_vars[i][j] * distance[i][j] * event_matrix[j]["total_event"] for (i, j) in routes)

        # CONSTRAINTS

        for j in demands:
            prob += lpSum(amount_vars[i][j] for i in supplies) == 1

        for i in demands:
            for j in supplies:
                prob += amount_vars[j][i] <= event_matrix[i]["total_event"] * wh_vars[j]

        prob += lpSum(wh_vars[i] for i in supplies) == number_of_loc

        prob.solve(PULP_CBC_CMD(msg=0))

        results = self.prepare_data_tables(prob, frequency_data)

        with open('optimal_locations.pickle', 'wb') as handle:
            pickle.dump(results, handle, protocol=pickle.HIGHEST_PROTOCOL)

        logging.info(
            """
            You have successfully run the algorithm. To see the optimization results, you can run 
            object_name.supply_data or object_name.optimal_data 
            OR
            You can run optimal_loc.visualize() command to see the results on a map.
            """
        )
