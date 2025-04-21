import requests
from bs4 import BeautifulSoup


def scrape_merck_vet_manual_sections():
    url = "https://www.merckvetmanual.com/ear-disorders/deafness/deafness-in-animals"

    # Send HTTP request to the website
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to retrieve the page: Status code {response.status_code}")
        return

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")
    print("soupp: ", soup)
    # Find the sections container - this may need adjustment based on actual HTML structure
    sections_container = soup.find("div", class_="sections") or soup.find(id="sections")
    print("sections_container: ", sections_container)
    # If we can't find the specific container, look for all links in the sections area
    if not sections_container:
        # Look for links that appear to be sections based on the URL pattern
        section_links = soup.find_all(
            "a", href=lambda href: href and "/veterinary-topics/" in href
        )
    else:
        section_links = sections_container.find_all("a")

    # Extract and store section titles and URLs
    sections = []
    for link in section_links:
        title = link.text.strip()
        url = link.get("href")

        # If URL is relative, make it absolute
        if url and not url.startswith("http"):
            url = f"https://www.merckvetmanual.com{url}"

        sections.append({"title": title, "url": url})

    return sections


if __name__ == "__main__":
    sections = scrape_merck_vet_manual_sections()
    print("se   : ", sections)
    if sections:
        print(f"Found {len(sections)} sections:")
        for section in sections:
            print(f"Title: {section['title']}")
            print(f"URL: {section['url']}")
            print("-" * 30)
    else:
        print("No sections found or there was an error during scraping.")
