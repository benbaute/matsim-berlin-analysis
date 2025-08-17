import xml.etree.ElementTree as ET
import gzip
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import LineString

version = "03"
base_path = f"../matsim-berlin/output/berlin-v6.4-1pct-{version}/"
file_path = base_path + "berlin-v6.4.output_plans.xml.gz"
output_file = "output/bike_routes.geojson"

# Load
network = gpd.read_file("../matsim-berlin/output/network/cycle-highway-network/bike-links.geojson")
network["length"] = pd.to_numeric(network["length"])
network_lookup = {}
for _, d in network.iterrows():
    network_lookup[d["id"]] = {"length": d["length"], "geometry": d["geometry"]}

rows = []

with gzip.open(file_path, 'rt', encoding='utf-8') as f:
    tree = ET.parse(f)
    root = tree.getroot()

    for person in root.findall('person'):
        person_id = person.attrib['id']
        for plan in person.findall('plan'):
            selected = plan.attrib.get('selected', 'no')
            for elem in plan:
                if elem.tag == 'leg':
                    mode = elem.attrib.get('mode')
                    if mode == "bike":
                        route = elem.find('route')
                        if route is not None and route.text:
                            link_ids = route.text.strip().split()
                            rsv_length, non_rsv_length = 0, 0
                            coords = []
                            for lid in link_ids:
                                link = network_lookup.get(lid)
                                coords.extend(list(link["geometry"].coords))
                                length = link["length"]
                                if "link_RSV" in lid:
                                    rsv_length += length
                                else:
                                    non_rsv_length += length

                            geom = LineString(coords)

                            rows.append({
                                "person_id": person_id,
                                "plan_selected": selected,
                                "mode": mode,
                                "link_sequence": route.text.strip(),
                                "geometry": geom,
                                "length": rsv_length + non_rsv_length,
                                "rsv_usage": rsv_length / (rsv_length+non_rsv_length) * 100
                            })

plans_gdf = gpd.GeoDataFrame(rows, crs=network.crs)
plans_gdf.to_file(Path(output_file))
