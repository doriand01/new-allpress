from allpress.core.database import DatabaseService
from allpress.services.vectors import VectorDB
from allpress.services import scrape, nlp
from allpress.services.search import Searcher
from allpress.settings import TEMP_TRAINING_VECTOR_PATH, CLASSIFICATION_MODELS_PATH

from urllib3 import exceptions as urllib3_exceptions
from requests import exceptions as requests_exceptions

import torch

from random import shuffle
from os import path
import argparse

semantic_temp_path = path.join(TEMP_TRAINING_VECTOR_PATH, "semantic.pth")
rhetoric_temp_path = path.join(TEMP_TRAINING_VECTOR_PATH, "rhetoric.pth")

semantic_autoencoder_path = path.join(CLASSIFICATION_MODELS_PATH, "semantic_autoencoder.pth")
rhetoric_autoencoder_path = path.join(CLASSIFICATION_MODELS_PATH, "rhetoric_autoencoder.pth")

db_service = DatabaseService()
vector_db = VectorDB()

def _build_temp_embed_tensor():
    ## Responsible for executing the command `build_temp` from the CLI.


    # First, all news sources are pulled from the DB for scraping.
    db_service.db.cursor.execute("SELECT * FROM newssource;")
    sources = db_service.db.cursor.fetchall()[1:]

    # If we assume the table is quite large and has many sources, we want to avoid introducing bias into the autoencoder
    # by including too many articles from rows near the top of the table. For this reason, we shuffle the sources
    # loaded from the DB before scraping.
    shuffle(sources)
    scraper = scrape.Scraper()

    # Location of temp tensors as defined in settings is saved to a string for later writing

    tensors_saved = 0
    for source, url in sources:
        try:
            scraped = scraper.scrape(url)
            for batch in scraped:

                # Inside this loop, the scraped articles have their embeddings generated (using LaBSE and paraphrase)
                # then, newly scraped tensors (if any are found) are saved to disk for later retrieval.

                embeds = batch.generate_embeddings()
                semantic_embeds = embeds.semantic[0][0]
                rhetoric_embeds = embeds.rhetoric[0][0]

                if not path.exists(semantic_temp_path) and semantic_embeds.size > 0:
                    write_tensor = torch.tensor(semantic_embeds)
                    torch.save(write_tensor, semantic_temp_path)
                elif path.exists(semantic_temp_path):
                    saved_tensor = torch.load(semantic_temp_path)
                    new_tensors = torch.tensor(semantic_embeds)
                    write_tensor = torch.cat((saved_tensor, new_tensors))
                    torch.save(write_tensor, semantic_temp_path)

                if not path.exists(rhetoric_temp_path) and rhetoric_embeds.numel() > 0:
                    write_tensor = torch.tensor(rhetoric_embeds)
                    torch.save(write_tensor, rhetoric_temp_path)
                elif path.exists(rhetoric_temp_path):
                    saved_tensor = torch.load(rhetoric_temp_path)
                    new_tensors = torch.tensor(rhetoric_embeds)
                    write_tensor = torch.cat((saved_tensor, new_tensors))
                    torch.save(write_tensor, rhetoric_temp_path)

                tensors_saved += semantic_embeds.size + len(rhetoric_embeds)

        except (urllib3_exceptions.MaxRetryError,
                urllib3_exceptions.NameResolutionError,
                requests_exceptions.ConnectionError) as e:
            print(f"Scraping {url} failed: {e}")

        except KeyboardInterrupt:
            # Add exception handling here later?
            print(f"{tensors_saved} tensors saved")
            pass

def _train_autoencoders(epochs):
    semantic_training_tensor = torch.load(semantic_temp_path)
    rhetoric_training_tensor = torch.load(rhetoric_temp_path)

    semantic_model = nlp.encoders.train_autoencoder(
        semantic_training_tensor,
        epochs=epochs,
        latent_dim=128)

    rhetoric_model = nlp.encoders.train_autoencoder(
        rhetoric_training_tensor,
        epochs=epochs,
        latent_dim=256
    )

    torch.save(semantic_model, semantic_autoencoder_path)
    torch.save(rhetoric_model, rhetoric_autoencoder_path)

def _scrape_sources(shuffle_data: bool, save_vectors: bool, iterations: int):
    db_service.db.cursor.execute("SELECT * FROM newssource;")
    sources = db_service.db.cursor.fetchall()[1:] # Start from 2nd element to exclude label row
    if shuffle_data: shuffle(sources)

    scraper = scrape.Scraper()
    semantic_autoencoder = torch.load(semantic_autoencoder_path, weights_only=False)
    rhetoric_autoencoder = torch.load(rhetoric_autoencoder_path, weights_only=False)
    for source, url in sources:
        try:
            scraped = scraper.scrape(url, iterations=iterations)
            for batch in scraped:
                # generate_embeddings() returns a tuple containing the semantic, and rhetorical embedddings, as tuples.
                # The semantic and rhetorical embedding tuples contain the embedding itself, and the article id of
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

                # Autoencode embeddings

                if save_vectors:

                    with torch.no_grad():

                        sem_autoencoded = semantic_autoencoder.encode(torch.Tensor(semantic_vecs))
                        rhet_autoencoded = rhetoric_autoencoder.encode(torch.Tensor(rhetoric_vecs))

                    vector_db.insert_vectors(sem_autoencoded, semantic_ids, write_to='semantic')
                    vector_db.insert_vectors(rhet_autoencoded, rhetoric_ids, write_to='rhetoric')

                for page in pages:
                    try:
                        page.save()
                    except Exception as e:
                        print(f"Error saving article from {page.page_url}: {e}")
        except Exception as e:
            print(f"Failed to scrape {source}: {e}")
    if not sources:
        print("No sources found.")
        return


def _search(query: str, top_k1: int, top_k2: int):
    searcher = Searcher(top_k1, top_k2)
    searcher.search(query)