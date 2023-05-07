import streamlit as st
from pandas import DataFrame
from streamlit_folium import folium_static
from pickle import load as pickle_load
from folium import plugins, Map, CircleMarker, Marker, Icon
from PIL import Image

my_algorithm = Image.open('../Modelling Algorithm.png')

st.set_page_config(layout="wide")

my_colours = [
    'darkred',
    'orange',
    'darkgreen',
    'darkblue',
    'purple',
    'lightgreen',
    'pink',
    'lightblue',
    'black'
]


@st.cache_data
def read_data(my_json):
    with open(my_json, 'rb') as handle:
        output_distances = pickle_load(handle)
    return output_distances


st.sidebar.text('')
st.sidebar.text('')
st.sidebar.text('')

### SEASON RANGE ###
st.sidebar.markdown("**First select the station number you want to analyze:** 👇")

analysis_result = read_data("optimal_locations.pickle")

optimal_data = DataFrame(analysis_result["optimal_data"])
supply_data = DataFrame(analysis_result["supply_data"])

optimal_data["supply_group"] = optimal_data.groupby(['supply_hexagon_id']).ngroup()
optimal_data["my_colours"] = optimal_data["supply_group"].apply(lambda x: my_colours[x % (len(my_colours))])

st.sidebar.text('')
agree = st.sidebar.checkbox('Show Model Algorithm')
st.sidebar.text('')
st.sidebar.text('')
st.sidebar.write("[MODELLING CODE](https://sinan-demirhan.github.io/ALL-PROJECTS/Projects/BOSTON%20OPTIMIZATION.html)")
st.sidebar.text('')
st.sidebar.text('')


# st.sidebar.download_button(
#      label="Download Raw Data",
#      data=supply_data,
#      file_name='Optimal Locations.csv',
#      mime='text/csv',
#  )


def plotting_main_map(optimization_data: DataFrame,
                      optimal_loc_data: DataFrame
                      ):

    plot_center = [optimization_data["hex_lat"].median(), optimization_data["hex_lon"].median()]
    my_map = Map(location=plot_center, zoom_start=12)

    for j, i in optimal_data.iterrows():
        CircleMarker([i["hex_lat"], i["hex_lon"]],
                     radius=5,
                     color=i["my_colours"]).add_to(my_map)

    for j, i in optimal_loc_data.iterrows():
        Marker([i["hex_lat"], i["hex_lon"]], radius=5,
               icon=Icon(color='red', icon='info-sign')).add_to(my_map)

    plugins.Fullscreen(position='topleft').add_to(my_map)

    return my_map


if not agree:
    row_spacer1, row_1, row_spacer2 = st.columns((2, 6, 2))

    with row_1:
        st.text("There are {} optimal locations".format(len(supply_data)))
        folium_static(plotting_main_map(optimal_data, supply_data))
        st.text("")
        st.text("")
else:
    st.image(my_algorithm, caption='The Algorithm', width=1000)
