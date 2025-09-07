from allpress.config import check_config
from allpress.db.io import connection, cursor, VectorDB
from allpress.net import scrape
from allpress.nlp.encoders import train_semantic_autoencoder, train_rhetorical_autoencoder, load_vectors_in_batches

import torch
import numpy as np
import traceback

cursor.execute('USE test;') # Placeholder name, should be replaced with actual database name
vector_db = None

from random import shuffle # remove later

class CLI:
    def __init__(self):
        pass

    # Add option to enable build_vectors parameter. Set to true by default here for testing.
    def scrape_sources(self, start_from=0, build_vectors=True):
        cursor.execute("SELECT * FROM newssource;")
        sources = cursor.fetchall()[1:]
        shuffle(sources) #remove later
        scraper = scrape.Scraper()
        vector_db = VectorDB()
        for source, url in sources[start_from:]:
            print(f"Scraping {source} from {url}...")
            try:
                scraped = scraper.scrape(url, iterations=2)
                print(f"Finished scraping {source}.")
                for batch in scraped:
                    embeds = batch.generate_embeddings()
                    pages = batch.serialize()
                    if build_vectors:
                        vector_db.insert_vectors(embeds)
                    for page in pages:
                        try:
                            page.save()
                            print(f"Saved article from {page.page_url} to the database.")
                        except Exception as e:
                            print(f"Error saving article from {page.page_url}: {e}")
            except Exception as e:
                print(f"Failed to scrape {source}: {e}")
                print(traceback.format_exc())
        if not sources:
            print("No sources found.")
            return


    def run(self):
        while True:
            command = input("allpress>: ").strip().lower()
            if not command:
                check_config()
            elif "scrape" in command:
                if len(command.split(" ")) > 1:
                    self.scrape_sources(start_from=int(command.split(" ")[1]))
                else:
                    self.scrape_sources()
            elif command == "train":
                train_semantic_autoencoder(128, 50, 1e-3) # Remove magic numbers. Maybe add a config
                train_rhetorical_autoencoder(256, 100, 1e-3) # for latent vector shape?
            elif command == "build vectordb":
                sem_autoencoder = torch.load(r"C:\Users\Dorian\PycharmProjects\Allpress\src\allpress\models\autoencoders\semantic_model.pth", weights_only=False)
                rhet_autoencoder = torch.load(r"C:\Users\Dorian\PycharmProjects\Allpress\src\allpress\models\autoencoders\rhetoric_model.pth", weights_only=False)
                vector_db = VectorDB()
                sem_vecs = np.stack([sem_autoencoder.encode(vec).detach().numpy() for vec in load_vectors_in_batches('sem_vec')]).astype("float32")
                rhet_vecs = np.stack([rhet_autoencoder.encode(vec).detach().numpy() for vec in load_vectors_in_batches('rhet_vec')]).astype("float32")
                rhet_vecs = rhet_vecs.squeeze(1)
                sem_vecs = sem_vecs.squeeze(1)
                uids = [uid for uid in load_vectors_in_batches('uid')]

                vector_db.insert_vectors(rhet_vecs, sem_vecs, uids)
            elif command == "build vectormap":
                sem_autoencoder = torch.load(r"C:\Users\Dorian\PycharmProjects\Allpress\src\allpress\models\autoencoders\semantic_model.pth", weights_only=False)
                rhet_autoencoder = torch.load(r"C:\Users\Dorian\PycharmProjects\Allpress\src\allpress\models\autoencoders\rhetoric_model.pth", weights_only=False)
            elif command == "exit":
                exit(0)
