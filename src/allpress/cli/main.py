from allpress.config import check_config
from allpress.db.io import connection, cursor, VectorDB
from allpress.net import scrape
from allpress.nlp.encoders import train_semantic_autoencoder, train_rhetorical_autoencoder, load_vectors_in_batches

import torch
import numpy as np

cursor.execute('USE test;') # Placeholder name, should be replaced with actual database name
vector_db = None


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
            command = input("allpress>: ").strip().lower()
            if not command:
                check_config()
            elif command == "scrape":
                self.scrape_sources()
            elif command == "train":
                train_semantic_autoencoder(32, 500, 1e-3)
                train_rhetorical_autoencoder(32, 500, 1e-3)
            elif command == "build vectordb":
                sem_autoencoder = torch.load(r"C:\Users\preit\OneDrive\Desktop\coding projects\Allpress2\src\allpress\models\autoencoders\semantic_model.pth", weights_only=False)
                rhet_autoencoder = torch.load(r"C:\Users\preit\OneDrive\Desktop\coding projects\Allpress2\src\allpress\models\autoencoders\rhetoric_model.pth", weights_only=False)
                vector_db = VectorDB()
                sem_vecs = np.stack([sem_autoencoder.encode(vec).detach().numpy() for vec in load_vectors_in_batches('sem_vec')]).astype("float32")
                rhet_vecs = np.stack([rhet_autoencoder.encode(vec).detach().numpy() for vec in load_vectors_in_batches('rhet_vec')]).astype("float32")
                rhet_vecs = rhet_vecs.squeeze(1)
                uids = [uid for uid in load_vectors_in_batches('uid')]

                vector_db.insert_vectors(rhet_vecs, sem_vecs, uids)
            elif command == "exit":
                exit(0)
