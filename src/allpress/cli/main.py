from allpress.config import check_config
from allpress.db.io import connection, cursor, VectorDB
from allpress.net import scrape
from allpress.nlp.encoders import train_semantic_autoencoder, train_rhetorical_autoencoder, load_vectors_in_batches
from allpress.settings import CLASSIFICATION_MODELS_PATH, FAISS_INDEX_PATH

import torch
import numpy as np
import traceback

from random import shuffle # remove later
from os import path

from allpress.types import EmbeddingResult

cursor.execute('USE test;') # Placeholder name, should be replaced with actual database name
vector_db = None
semantic_autoencoder = torch.load(path.join(CLASSIFICATION_MODELS_PATH, 'semantic_model.pth'))
rhetoric_autoencoder = torch.load(path.join(CLASSIFICATION_MODELS_PATH, 'rhetoric_model.pth'))

semantic_autoencoder.to('cpu')
rhetoric_autoencoder.to('cpu')

class CLI:
    def __init__(self):
        pass

    def parse_arguments(self, command):
        pass

    # Add option to enable build_vectors parameter. Set to true by default here for testing.
    def scrape_sources(self, start_from=0, build_vectors=True):
        cursor.execute("SELECT * FROM newssource;")
        sources = cursor.fetchall()[1:]
        shuffle(sources) #remove later
        scraper = scrape.Scraper()
        vector_db = VectorDB()

        # Save counters are for debug
        pages_saved = 0
        sem_vectors_saved = 0
        rhetoric_vectors_saved = 0
        try:
            for source, url in sources[start_from:]:
                try:
                    scraped = scraper.scrape(url, iterations=2)
                    for batch in scraped:
                        # generate_embeddings() returns a tuple containing the semantic, and rhetorical embedddings, as tuples.
                        # The semantical and rhetorical embedding tuples contain the embedding itself, and the article id of
                        # the embeddings.

                        # Skips embedding and serialization process if batch of articles is empty.
                        if not batch:
                            continue

                        # Gather up embeddings and serialize pages.
                        embeds = batch.generate_embeddings()
                        pages = batch.serialize()
                        semantic_vecs = embeds.semantic[0][0]
                        semantic_ids = embeds.semantic[0][1]
                        rhetoric_vecs = embeds.rhetoric[0][0]
                        rhetoric_ids = embeds.rhetoric[0][1]

                        #Autoencode embeddings
                        with torch.no_grad():
                            sem_autoencoded = semantic_autoencoder.encode(torch.Tensor(semantic_vecs))
                            rhet_autoencoded = rhetoric_autoencoder.encode(torch.Tensor(rhetoric_vecs))

                        vector_db.insert_vectors(sem_autoencoded, semantic_ids, write_to='semantic')
                        sem_vectors_saved += len(sem_autoencoded)
                        vector_db.insert_vectors(rhet_autoencoded, rhetoric_ids, write_to='rhetoric')
                        rhetoric_vectors_saved += len(rhet_autoencoded)
                        print(f"Semantic vectors saved: {len(sem_autoencoded)}")
                        print(f"Rhetoric vectors saved: {len(rhet_autoencoded)}")
                        print(f"Site: {url}")
                        for page in pages:
                            try:
                                page.save()
                                pages_saved += 1 # For debug
                            except Exception as e:
                                print(f"Error saving article from {page.page_url}: {e}")
                except Exception as e:
                    print(f"Failed to scrape {source}: {e}")
            if not sources:
                print("No sources found.")
                return
        except Exception:
            print(f"""Process aborted. Saved {sem_vectors_saved} sem vectors and {rhetoric_vectors_saved} rhetoric vectors across {pages_saved} pages.""")


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
