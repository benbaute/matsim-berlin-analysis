import geopandas as gpd

base_path = "../matsim-berlin/output/network/"
nodes_gdf = gpd.read_file(f"{base_path}python/new_matsim_nodes_combined.geojson")
links_network = gpd.read_file(f"{base_path}python/new_matsim_links_network_intersections.geojson")
links_cycle = gpd.read_file(f"{base_path}python/new_matsim_links_cycle_highways.geojson")
bike_network_intersections_gdf = gpd.read_file(f"{base_path}python/intersection_nodes.geojson")
bike_network_intersections_gdf["orig_point"] = bike_network_intersections_gdf.geometry.apply(lambda mp: mp.geoms[0])
bike_network_intersections_gdf["moved_point"] = bike_network_intersections_gdf.geometry.apply(lambda mp: mp.geoms[1])
bike_network_intersections_gdf["geometry"] = bike_network_intersections_gdf["moved_point"]

node_map = nodes_gdf.explore(color="blue", marker_kwds={"radius": 12})
links_network_map = links_network.explore(m=node_map, color="red", style_kwds={"weight": 8})
links_cycle_map = links_cycle.explore(m=links_network_map, color="green", style_kwds={"weight": 6})
complete_map = bike_network_intersections_gdf.explore(m=links_cycle_map, color="yellow",  marker_kwds={"radius": 8})
complete_map.save("output/map.html")


