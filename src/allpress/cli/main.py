from allpress.config import check_config
from allpress.db.io import connection, cursor
from allpress.net import scrape

cursor.execute('USE test;') # Placeholder name, should be replaced with actual database name

class CLI:
    def __init__(self):
        pass

    def scrape_sources(self):
        cursor.execute("SELECT * FROM newssource;")
        sources = cursor.fetchall()[1:]
        scraper = scrape.Scraper()
        for source, url in sources:
            print(f"Scraping {source} from {url}...")
            try:
                scraped = scraper.scrape(url, iterations=2)
                print(f"Finished scraping {source}.")
                for batch in scraped:
                    batch.generate_embeddings()
                    pages = batch.serialize()
                    for page in pages:
                        try:
                            page.save()
                            print(f"Saved article from {page.page_url} to the database.")
                        except Exception as e:
                            print(f"Error saving article from {page.page_url}: {e}")
            except Exception as e:
                print(f"Failed to scrape {source}: {e}")
        if not sources:
            print("No sources found.")
            return


    def run(self):
        while True:
            try:
                command = input("allpress>: ").strip().lower()
                if not command:
                    check_config()
                elif command == "scrape":
                    self.scrape_sources()
            except Exception as e:
                print(f"Error: {e}")