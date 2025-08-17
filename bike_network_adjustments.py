from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.ops import split, snap
from shapely.geometry import MultiPoint

base_path = "../matsim-berlin/output/network/"
nodes_gdf = gpd.read_file(f"{base_path}bike/bike-nodes.geojson")
links_gdf = gpd.read_file(f"{base_path}bike/bike-links.geojson")
links_gdf["length"] = pd.to_numeric(links_gdf["length"])
links_lookup = {}
for _, d in links_gdf.iterrows():
    links_lookup[d["id"]] = {"fromID": d["fromID"], "toID": d["toID"], "length": d["length"], "geometry": d["geometry"]}
intersection_gdf = gpd.read_file(f"{base_path}qgis-output/bike-network-intersections.geojson")

intersection_node_ids = []
is_new_node = []
intersection_moved_geometries = []
new_node_counter = 0
to_be_deleted = []
new_matsim_links = []
new_matsim_nodes = []
new_matsim_nodes_lookup = {}
new_matsim_links_lookup = {}
active_nodes_lookup = dict(zip(nodes_gdf["id"], nodes_gdf["geometry"]))

snap_threshold = 2  # meters
tolerance = 1e-5
for _, intersection in intersection_gdf.iterrows():
    intersection_geom = intersection["geometry"]
    nearest_indices = nodes_gdf.sindex.nearest(intersection_geom, return_all=False, max_distance=snap_threshold)

    if nearest_indices.size > 0:  # Snap to nearest node
        nearest_index = nearest_indices[1][0]
        node = nodes_gdf.iloc[nearest_index]
        intersection_node_ids.append(node["id"])
        is_new_node.append(False)
        intersection_moved_geometries.append(node["geometry"])
    else:

        def find_link(intersection_link_id):
            if intersection_link_id in new_matsim_links_lookup:
                links = new_matsim_links_lookup.get(intersection_link_id)
                for link in links:
                    if link["geometry"].distance(intersection_geom) < tolerance:
                        links.remove(link)
                        return link, links
                raise ValueError(f"Unexpected Link. {intersection_link_id}")
            elif intersection_link_id in links_lookup:
                return links_lookup.get(intersection_link_id), []
            raise ValueError(f"Unknown link: {intersection_link_id}")


        # Find link containing point
        link_id = intersection["id_2"]
        to_be_deleted_link, link_array = find_link(link_id)

        # Create new node
        new_node_id = f"node_{intersection['id']}_{new_node_counter}"
        if intersection_geom in new_matsim_nodes_lookup:
            new_node_id = new_matsim_nodes_lookup[intersection_geom]
        else:
            new_link = {
                "id": new_node_id,
                "geometry": intersection_geom
            }
            new_matsim_nodes.append(new_link)
            new_matsim_nodes_lookup[intersection_geom] = new_node_id
            new_node_counter += 1
            active_nodes_lookup[new_node_id] = intersection_geom

        split_parts = split(snap(to_be_deleted_link["geometry"], intersection_geom, tolerance), intersection_geom)
        part_a, part_b = split_parts.geoms
        from_point = active_nodes_lookup[to_be_deleted_link["fromID"]]
        if from_point.distance(part_b) < from_point.distance(part_a):
            part_a, part_b = part_b, part_a

        length_complete_link = to_be_deleted_link["length"] if (
                "length" in to_be_deleted_link) else to_be_deleted_link["euclideanDistance"]
        part_a_length = part_a.length / (part_a.length + part_b.length) * length_complete_link
        part_b_length = part_b.length / (part_a.length + part_b.length) * length_complete_link
        first_link = {
            "id": f"link_{len(link_array)}1_{link_id}",
            "fromID": to_be_deleted_link["fromID"],
            "toID": new_node_id,
            "geometry": part_a,
            "originalLinkID": link_id,
            "euclideanDistance": part_a_length
        }
        second_link = {
            "id": f"link_{len(link_array)}2_{link_id}",
            "fromID": new_node_id,
            "toID": to_be_deleted_link["toID"],
            "geometry": part_b,
            "originalLinkID": link_id,
            "euclideanDistance": part_b_length
        }
        new_matsim_links.append(first_link)
        new_matsim_links.append(second_link)
        link_array.append(first_link)
        link_array.append(second_link)
        new_matsim_links_lookup[link_id] = link_array

        intersection_node_ids.append(new_node_id)
        is_new_node.append(True)
        intersection_moved_geometries.append(intersection_geom)

base_path += "python/"
intersection_gdf["nodeID"] = pd.Series(intersection_node_ids)
intersection_gdf["isNew"] = pd.Series(is_new_node)
intersection_gdf["geometry"] = [
    MultiPoint([orig, moved])
    for orig, moved in zip(intersection_gdf.geometry, intersection_moved_geometries)
]
intersection_gdf.to_file(Path(f"{base_path}intersection_nodes.geojson"))

new_matsim_links_gdf = gpd.GeoDataFrame(new_matsim_links, crs=nodes_gdf.crs)
new_matsim_links_gdf.to_file(Path(f"{base_path}new_matsim_links_network_intersections.geojson"))

new_matsim_nodes_gdf = gpd.GeoDataFrame(new_matsim_nodes, crs=nodes_gdf.crs)
new_matsim_nodes_gdf.to_file(Path(f"{base_path}new_matsim_nodes_network_intersections.geojson"))

print(f"New nodes: {new_matsim_nodes_gdf.size}, new links: {new_matsim_links_gdf.size}")
