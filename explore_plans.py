import geopandas as gpd
import pandas as pd
import folium
from matplotlib import cm, colors
from shapely import LineString


network = gpd.read_file("../matsim-berlin/output/network/cycle-highway-network/bike-links.geojson")
network = network.to_crs(epsg=4326)
plans_gdf = gpd.read_file("output/bike_routes.geojson")
plans_gdf["length"] = round(plans_gdf["length"], 2)
plans_gdf["rsv_usage"] = round(plans_gdf["rsv_usage"], 2)

plans_gdf["link_sequence"] = plans_gdf["link_sequence"].str.split()
plans_gdf = plans_gdf.to_crs(epsg=4326)

filtered = [
    {"df": plans_gdf[plans_gdf["length"] < 5000], "rpm": 500, "maps": []},
    {"df": plans_gdf[(plans_gdf["length"] < 10000) & (plans_gdf["length"] >= 5000)], "rpm": 100, "maps": []},
    {"df": plans_gdf[(plans_gdf["length"] < 15000) & (plans_gdf["length"] >= 10000)], "rpm": 50, "maps": []},
    {"df": plans_gdf[plans_gdf["length"] >= 15000], "rpm": 15, "maps": []}
]

for f in filtered:
    number_of_routes = len(f["df"])
    print(number_of_routes)
    for i in range(0, number_of_routes, f["rpm"]):
        # Base map
        m = folium.Map(location=[52.5, 13.4], zoom_start=12)
        f["maps"].append(m)

# Draw network in gray
for _, row in network.iterrows():
    if "link_RSV" in row["id"]:
        for f in filtered:
            for m in f["maps"]:
                folium.GeoJson(row["geometry"], style_function=lambda x: {"color": "green", "weight": 7}).add_to(m)

cmap = cm.plasma
for f_index, f in enumerate(filtered):
    df = f["df"]
    number_of_routes = len(df)
    route_index = 0

    for m_index, m in enumerate(f["maps"]):
        end_index = min(number_of_routes, f["rpm"] + route_index)
        current_df = df.iloc[route_index:end_index].copy()
        current_df["index"] = range(route_index, end_index)
        norm = colors.Normalize(vmin=route_index, vmax=end_index - 1)
        route_index = end_index

        def style_function(feature):
            idx = feature["properties"]["index"]
            rgba = cmap(norm(idx))
            return {
                "color": colors.to_hex(rgba),
                "weight": 3,
            }

        folium.GeoJson(
            current_df,
            style_function=style_function,
            tooltip=folium.features.GeoJsonTooltip(fields=["index", "person_id", "plan_selected", "length", "rsv_usage"])
        ).add_to(m)

        m.save(f"output/plans_map/{f_index}_{m_index}.html")
