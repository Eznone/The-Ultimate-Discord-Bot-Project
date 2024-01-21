import requests as req
from bs4 import BeautifulSoup


def getSongs(first, last):
  source = req.get("https://www.billboard.com/charts/hot-100/")

  soup = BeautifulSoup(source.text, "html.parser")
  chart = soup.find(
    "div", {
      "class":
      "chart-results-list // lrv-u-padding-t-150 lrv-u-padding-t-050@mobile-max"
    })
  list = chart.find_all("div", {"class": "o-chart-results-list-row-container"},
                        limit=last)
  songs = []
  for i, el in enumerate(list[first:]):
    author = el.find_all("span", {"class": "c-label"})
    name = el.find("h3", {"id": "title-of-a-story"}).get_text().strip()
    author = author[1].get_text().strip()
    song = {"name": name, "author": author, "num": i + 1 + first}
    songs.append(song)

  return songs
