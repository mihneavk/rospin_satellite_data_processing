from hda import Client, Configuration
import os

conf = Configuration(user = "logimap", password = "dvga!vgdva2@A")
hda_client = Client(config = conf)


query = {
  "dataset_id": "EO:EEA:DAT:CLC-PLUS",
  "bbox": [
    25.507453552489714,
    46.69218214411508,
    25.525340679119644,
    46.69987625332544
  ],
  "productType": "Raster Layer",
  "resolution": "10m",
  "year": "2023",
  "itemsPerPage": 200,
  "startIndex": 0
}


# Ask the result for the query passed in parameter
matches = hda_client.search(query)

# List the results
print(matches)

# Download results in a directory (e.g. '/tmp')
matches.download(download_dir="./tmp")