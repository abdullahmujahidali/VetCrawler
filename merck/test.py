import requests
from bs4 import BeautifulSoup

url = "https://www.merckvetmanual.com/veterinary-topics"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")
print("soupppp: ", soup)
for letter_section in soup.select(".alpha-section"):
    letter = letter_section.find("h2").text.strip()
    topics = [a.text.strip() for a in letter_section.select("a")]
    print(f"{letter}: {topics}")
