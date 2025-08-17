import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, LineString

export_cycle_highways = True
input_file_name = "../matsim-berlin/output/network/bike-network.xml"
output_file_name_links = "../matsim-berlin/output/network/bike/bike-links.geojson"
output_file_name_nodes = "../matsim-berlin/output/network/bike/bike-nodes.geojson"
if export_cycle_highways:
    input_file_name = "../matsim-berlin/output/network/cycle-highways-bike-network.xml"
    output_file_name_links = "../matsim-berlin/output/network/cycle-highway-network/bike-links.geojson"
    output_file_name_nodes = "../matsim-berlin/output/network/cycle-highway-network/bike-nodes.geojson"
tree = ET.parse(input_file_name)
root = tree.getroot()

nodes = []
for node in root.find("nodes"):
    id_node, x_node, y_node = node.attrib['id'], node.attrib['x'], node.attrib['y']
    nodes.append({"id": id_node, "geometry": Point(x_node, y_node)})

nodes_gdf = gpd.GeoDataFrame(nodes, crs="EPSG:25832")
nodes_gdf.to_file(Path(output_file_name_nodes))

node_lookup = {n["id"]: n["geometry"] for n in nodes}

links = []
for link in root.find("links"):
    id_link, from_node_id, to_node_id, length, freeSpeed = (
        link.attrib['id'], link.attrib['from'], link.attrib['to'], link.attrib['length'], link.attrib['freespeed'])

    from_node_point = node_lookup[from_node_id]
    to_node_point = node_lookup[to_node_id]
    links.append({
        "id": id_link, "fromID": from_node_id, "toID": to_node_id, "length": length, "freeSpeed": freeSpeed,
        "geometry": LineString([[from_node_point.x, from_node_point.y], [to_node_point.x, to_node_point.y]])
    })

links_gdf = gpd.GeoDataFrame(links, crs="EPSG:25832")
links_gdf.to_file(Path(output_file_name_links))

