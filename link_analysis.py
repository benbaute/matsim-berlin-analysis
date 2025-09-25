import geopandas as gpd
import contextily as ctx
import pandas as pd
import folium
from matplotlib import cm, colors
import matplotlib.pyplot as plt
from shapely import wkt

version = "56"
base_path = f"../matsim-berlin/output/berlin-v6.4-1pct-{version}/"
file_path = base_path + "berlin-v6.4.output_links.csv.gz"
output_file = "output/bike_routes.geojson"

dataframe = pd.read_csv(file_path, sep=';', usecols=[
    "link", "from_node", "to_node", "length", "modes", "vol_bike", "geometry"])
dataframe["geometry"] = dataframe["geometry"].apply(wkt.loads)
links_gdf = gpd.GeoDataFrame(dataframe, geometry="geometry", crs="EPSG:25832")
links_gdf = links_gdf.to_crs(epsg=4326)
network = gpd.read_file("../matsim-berlin/output/network/cycle-highway-network/bike-links.geojson")
network = network.to_crs(epsg=4326)
rsv_links = []
for _, row in network.iterrows():
    if "link_RSV" in row["id"]:
        rsv_links.append(row)
rsv_links = gpd.GeoDataFrame(rsv_links)
rsv_links = rsv_links.set_crs(epsg=4326)

print(f"Number of all links: {len(links_gdf)}")
links_gdf = links_gdf[links_gdf["modes"] == "bike"]
print(f"Number of bike links: {len(links_gdf)}")
sorted_gdf = links_gdf.sort_values(by=['vol_bike'], ascending=False)

print("Most used link: ")
print(sorted_gdf.iloc[0])
for i in range(100):
    l = sorted_gdf.iloc[i]
    print(f"link: {l['link']}, vol_bike: {l['vol_bike']}")

cmap = cm.inferno
norm = colors.Normalize(vmin=0, vmax=links_gdf["vol_bike"].max())

threshold = 0  # 0.025 * links_gdf["vol_bike"].max()  # Use this for smooth interactive map.
above_threshold_gdf = links_gdf[links_gdf['vol_bike'] > threshold]
print(f"Number of bike links with volume > {threshold}: {len(above_threshold_gdf)}")


m = folium.Map(location=[52.5, 13.4], zoom_start=12)
folium.GeoJson(data=rsv_links, style_function=lambda x: {"color": "green", "weight": 7}).add_to(m)


def style_function(feature):
    idx = feature["properties"]["vol_bike"]
    rgba = cmap(norm(idx))
    return {
        "color": colors.to_hex(rgba),
        "weight": 3,
    }


folium.GeoJson(data=above_threshold_gdf,
               style_function=style_function,
               tooltip=folium.features.GeoJsonTooltip(fields=[
                   "link", "from_node", "to_node", "length", "vol_bike"])).add_to(m)
m.save(f"output/heat_map-{version}.html")

berlin_bbox = (13.11, 52.4, 13.63, 52.64)
links_berlin = above_threshold_gdf.cx[berlin_bbox[0]:berlin_bbox[2], berlin_bbox[1]:berlin_bbox[3]]

fig, ax = plt.subplots(figsize=(11, 6))
rsv_links.plot(color="green", linewidth=5.0, ax=ax)
links_berlin.plot(
    column="vol_bike",
    cmap=cmap,
    linewidth=1.5,
    ax=ax,
    legend=True,
    norm=norm
)

minx, miny, maxx, maxy = links_berlin.total_bounds
pad = 0.015
ax.set_xlim(minx + pad, maxx - pad)
ax.set_ylim(miny + pad, maxy - pad)
ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=links_gdf.crs.to_string())

ax.axis('off')

plt.tight_layout()
plt.savefig(f"output/heat_map-{version}.png", dpi=300)
