
from pathlib import Path
import feedparser
import yaml

CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "rss_sources.yaml"
)


def main():
    with open(CONFIG_PATH, encoding="utf-8") as file:
        config = yaml.safe_load(file)

    for source in config["sources"]:
        section = source["section"]
        url = source["url"]

        print(f"\nSección: {section}")

        if not url:
            print("Pendiente: configurar URL RSS")
            continue

        feed = feedparser.parse(url)

        if feed.bozo:
            print(f"Advertencia de lectura: {feed.bozo_exception}")

        print(f"Noticias encontradas: {len(feed.entries)}")

        for news in feed.entries[:3]:
            print("-", news.get("title", "Sin título"))


if __name__ == "__main__":
    main()
