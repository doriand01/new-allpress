# September 2025

### 0.5.0a (2025-09-24)

- Cleaning up code, separation of concerns
- Implement use of argparser for proper CLI behavior

### 0.4.5a (2025-09-17)

- Bug fixes
- Start work on primary key verification before article saves.
- Add faiss and .pth files to gitignore

### 0.4.4a (2025-09-13)

- Add comments

### 0.4.3a (2025-09-13)

- `allpress.db.models` removed
- Removed unused class in `allpress.db.search`
- Finished adding type-hinting for current codebase

### 0.4.2a (2025-09-13)

- `VectorDB._md5_to_uid()` function removed.
- Scraping, vector and article serialization pipelines updated.

### 0.4.1a (2025-09-07)

- Begin building pipeline for storage of individual named entities and sentences in the VectorDB.


# August 2025

### 0.4.0a (2025-08-08)

- `sem_vec` and `rhet_vec` columns have been removed from the `page` table
of the SQL database.
- `Article._rhetorical_mask()` removed. (Functionality reimplemented in
`Article._mask_rhetoric_chunks()`)
- `Article._semantic_mask()` removed.
- `VectorDB.insert_vectors()` refactored to work with new embedding logic.

# July 2025

### 0.3.3a (2025-07-22)

- Fix bug where semantic embeddings were still generated using paraphrase, rather than LaBSE

### 0.3.2a (2025-07-22)

- Separate model for semantic and rhetorical embedding.
- Rhetorical embedding now uses LaBSE, autoencoder for rhetorical embedded in 128-dim instead of 32.

### 0.3.1a (2025-07-17)

- Fixed IO bug that caused tensors saved to DB to be corrupted.

### 0.3.0a (2025-07-07)

- Begin work on FAISS search.
- Added config module for setting up application.
- Add very basic CLI implementation.

### 0.2.3a (2025-07-06)

- Semantic and rhetorical embedding of articles now done in batches.
- Other small optimizations to embedding calculations.

### 0.2.2a (2025-07-05)

- Added working implementation of DB io.

### 0.2.1a (2025-07-02)

- Begin work on DB and NLP processing
- Add unwritten changes from previous commit to changelog

### 0.2.0a (2025-07-01)

- Add `Article` object to represent articles
- Add AutoEncoder for semantic and rhetorical representation.

### 0.1.1a (2025-07-01)

- Add documentation for `scrape()` method of `Scraper`
- Small code changes

### 0.1.0a (2025-07-01)

- Initial release
- Added web scraper and article detector