import pooch
import requests
from bs4 import BeautifulSoup

# Base URL of the dataset
BASE_URL = "https://gin.g-node.org/NeuralEnsemble/ephy_testing_data/raw/master/openephysbinary/"


# Function to get file list
def get_file_list():
    url = "https://gin.g-node.org/NeuralEnsemble/ephy_testing_data/src/master/openephysbinary/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract file links
    file_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/NeuralEnsemble/ephy_testing_data/raw/master/openephysbinary/" in href:
            file_links.append(href.split("openephysbinary/")[-1])

    return file_links


# Get list of files in openephysbinary folder
file_list = get_file_list()
print(file_list)
# Setup Pooch
data_pooch = pooch.create(
    path=pooch.os_cache("ephy_testing_data"),  # Cache directory
    base_url=BASE_URL,
    registry={fname: None for fname in file_list},  # Registry with filenames
)

# Download all files
for filename in file_list:
    file_path = data_pooch.fetch(filename)
    print(f"Downloaded: {file_path}")
