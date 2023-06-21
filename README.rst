What is it?
-----------

The OptimalLoc package is a Python library designed to provide a
solution for finding optimal locations based on various needs such as
transportation and logistics, urban planning, retail, healthcare, and
emergency services. The package utilizes a mixed integer linear
optimization algorithm to calculate the optimal locations based on input
demands and a specified number of location points.

Main Features
-------------

-  Hexagon mapping: The package uses the Uber h3 library to map
   locations onto hexagons on a map. This allows for efficient
   optimization calculations by reducing the number of data points
   involved.
-  Event frequency calculation: The package calculates the frequency of
   events in each hexagonal region based on the provided input data.
   This information is used in the optimization algorithm to determine
   the optimal locations.
-  Distance data management: The package includes functionality to
   create and read distance data between pairs of hexagonal regions.
   This data can be stored in a database, such as MongoDB, or as a
   dataframe.
-  Optimization algorithm: The package utilizes a mixed integer linear
   optimization algorithm, implemented using the pulp library, to
   determine the optimal locations based on the given demands and the
   desired number of location points.
-  Visualization: The package provides a frontend app built with
   Streamlit to visualize the optimal results on a map. Users can
   interact with the app to analyze and understand the optimal
   locations.

Purpose of the Package
----------------------

The OptimalLoc package aims to assist various industries, including
logistics, retail, and emergency services, in optimizing their
operations by identifying the best locations for their needs. By finding
the optimal locations, organizations can improve efficiency, reduce
costs, and enhance their overall performance.

Getting Started
---------------

Installation
~~~~~~~~~~~~

To install the OptimalLoc package, you can use pip, the package
installer for Python:

.. code:: bash

   pip install optimal-loc

Usage
~~~~~

To use the OptimalLoc package for finding optimal locations, follow the
steps below:

1. Import the ``OptimalLoc`` class from the package:

   .. code:: python

      import optimal_loc

2. Create an instance of the ``OptimalLoc`` class:

   .. code:: python

      sol = optimal_loc.OptimalLoc()

3. Prepare your input data:

   -  Load your data into a pandas DataFrame, ensuring it includes the
      required columns for latitude and longitude information.
   -  Clean and preprocess the data as needed.

4. Create hexagon distance data:

   -  Call the ``create_hexagon_distance_data`` method of the
      ``OptimalLoc`` instance, providing your preprocessed data and
      specifying the hexagon size (‘small’, ‘medium’, or ‘big’).
   -  This step will calculate the hexagons on which the points in your
      data fall and create the necessary data to calculate distances
      between these hexagons.

   Example:
    .. code:: python

        sol.create_hexagon_distance_data(data, 'medium')

5. Read the distances:

   -  If you have a large distance dataset, you can store it in a
      MongoDB database and read it using the
      ``read_distances_from_mongodb`` method.
   -  Alternatively, you can directly read the distance data from a
      dataframe using the ``read_distances`` method.

   Example (reading from MongoDB):
    .. code:: python

        sol.read_distances_from_mongodb(mongo_client=MongoClient,
                                    mongo_database_name="db_name",
                                    mongo_collection_name="collection_name")

   Example (reading from a dataframe):
    .. code:: python

        sol.read_distances(read_from_dataframe=True, distance_dataframe=distance_data)

6. Calculate optimal locations:

   -  Call the ``calculate_optimal_locations`` method of the
      ``OptimalLoc`` instance, specifying the number of desired optimal
      locations and providing the distance and frequency data.
   -  This step will run the mixed integer linear optimization algorithm
      and calculate the optimal points or hexagon regions.

   Example:
    .. code:: python

        sol.calculate_optimal_locations(number_of_loc=5)

7. Access the results:

   -  After running the optimization algorithm, the optimal and supply
      data will be available in the ``optimal_data`` and ``supply_data``
      attributes of the ``OptimalLoc`` instance, respectively.

   Example:
    .. code:: python

        optimal_results = sol.optimal_data
        supply_results = sol.supply_data

8. Visualize the results:

   -  To visualize the optimal results on a map, you can call the
      ``visualize`` function from the ``optimal_loc.bash_command``
      module.

   Example:
    .. code:: python

        optimal_loc.visualize()

9. Explore and analyze the optimal locations using the provided
   Streamlit frontend app.

   Example:

   -  Open the app in a web browser using the displayed URL.
   -  Interact with the app to analyze the optimal locations visually
      and perform further analyses.

By following these steps, you can utilize the OptimalLoc package to find
optimal locations for various applications, such as transportation and
logistics, urban planning, retail, healthcare, and emergency services.

Contribution
------------

Contributions are welcome. Notice a bug let us know.

Author
------

-  Main Maintainer: Sinan Demirhan (SDemirhan)
