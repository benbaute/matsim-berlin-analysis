import geopandas as gpd
import pandas as pd

version = "04"
base_path = f"../matsim-berlin/output/berlin-v6.4-1pct-{version}/"
file_path = base_path + "berlin-v6.4.output_links.csv.gz"
output_file = "output/bike_routes.geojson"

links_df = pd.read_csv(file_path, sep=';', usecols=[
    "link", "from_node", "to_node", "length", "modes", "vol_bike", "geometry"])
links_gdf = gpd.GeoDataFrame(links_df)
print(f"Number of all links: {len(links_gdf)}")
links_gdf = links_gdf[links_df["modes"] == "bike"]
print(f"Number of bike links: {len(links_gdf)}")
links_gdf = links_gdf.sort_values(by=['vol_bike'], ascending=False)

print("Most used link: ")
print(links_gdf.iloc[0])
for i in range(100):
    l = links_gdf.iloc[i]
    print(f"link: {l['link']}, vol_bike: {l['vol_bike']}")

