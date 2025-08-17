from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.ops import split, snap
from shapely import Point, LineString, MultiPoint

base_path = "../matsim-berlin/output/network/"
cycle_highways_gdf = gpd.read_file(f"{base_path}qgis-output/snapped-cycle-highways.geojson")
bike_network_intersections_gdf = gpd.read_file(f"{base_path}python/intersection_nodes.geojson")
bike_network_intersections_gdf["orig_point"] = bike_network_intersections_gdf.geometry.apply(lambda mp: mp.geoms[0])
bike_network_intersections_gdf["moved_point"] = bike_network_intersections_gdf.geometry.apply(lambda mp: mp.geoms[1])
self_intersections_gdf = gpd.read_file(f"{base_path}qgis-output/self-intersections.geojson")
self_intersections_gdf["nodeID"] = self_intersections_gdf["id"] + "_" + self_intersections_gdf["id_2"]
self_intersections_gdf["selfIntersection"] = True

all_split_points = pd.concat([
    gpd.GeoDataFrame({"nodeID": bike_network_intersections_gdf["nodeID"],
                      "geometry": bike_network_intersections_gdf["orig_point"],
                      "selfIntersection": False}),
    self_intersections_gdf[["nodeID", "geometry", "selfIntersection"]]
]).drop_duplicates(subset=["geometry"]).reset_index(drop=True)
all_split_points_lookup = {}
for _, d in all_split_points.iterrows():
    all_split_points_lookup[d["geometry"]] = {"nodeID": d["nodeID"], "selfIntersection": d["selfIntersection"]}

split_lines = []
new_matsim_nodes = []
new_matsim_nodes_lookup = {}

tolerance = 1e-5
for _, cycle_highway in cycle_highways_gdf.iterrows():
    id_cycle_highway = cycle_highway["id"]
    line = cycle_highway.geometry
    # Find intersection points along drawn cycle-highway to split into links
    pts_on_line = [pt for pt in all_split_points["geometry"]
                   if line.distance(pt) < tolerance]
    points = sorted(pts_on_line, key=lambda p: line.project(p))

    current_line = snap(line, MultiPoint(points), tolerance)
    current_from_id = None

    for i, point in enumerate(points):
        # Split into two parts: before and after this point
        split_result = split(current_line, point)

        first_part = split_result.geoms[0]
        second_part = first_part
        if len(split_result.geoms) == 2:
            second_part = split_result.geoms[1]

        to_node = all_split_points_lookup[point]
        to_id = to_node["nodeID"]

        if to_node["selfIntersection"]:
            if point not in new_matsim_nodes_lookup:
                new_matsim_nodes_lookup[point] = to_node["nodeID"]
                new_matsim_nodes.append({
                    "id": to_node["nodeID"],
                    "geometry": point
                })

        if current_from_id is not None:
            split_lines.append({
                "id": f"link_{id_cycle_highway}_{i}",
                "geometry": first_part,
                "fromID": current_from_id,
                "toID": to_id,
                "euclideanDistance": first_part.length
            })


        current_line = second_part
        current_from_id = to_id

split_gdf = gpd.GeoDataFrame(split_lines, crs=cycle_highways_gdf.crs)
split_gdf.to_file(Path(f"{base_path}python/new_matsim_links_cycle_highways.geojson"))

new_matsim_nodes_self_intersections_gdf = gpd.GeoDataFrame(new_matsim_nodes, crs=cycle_highways_gdf.crs)
new_matsim_nodes_self_intersections_gdf.to_file(Path(f"{base_path}python/new_matsim_nodes_self_intersections.geojson"))

new_matsim_nodes_network_intersections_gdf = gpd.read_file(
    f"{base_path}python/new_matsim_nodes_network_intersections.geojson")

new_matsim_nodes_self_intersections_gdf["selfIntersection"] = True
new_matsim_nodes_network_intersections_gdf["selfIntersection"] = False
new_matsim_nodes_combined_gdf = pd.concat([
    new_matsim_nodes_network_intersections_gdf,
    new_matsim_nodes_self_intersections_gdf
]).reset_index(drop=True)
new_matsim_nodes_combined_gdf.to_file(Path(f"{base_path}python/new_matsim_nodes_combined.geojson"))
