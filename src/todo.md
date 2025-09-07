# To-Dos

## In Progress

- 040-002-020: Properly finish pipeline for new multi-vector representations
- 040-001-019: Refactor code to support multi-vector representations for documents, instead of single vector
representations.
- 033-001-018: Implement proper search function in CLI.
- 031-001-017: Scraper should respect robots.txt.
- 030-002-015: Write documentation and type hinting for entire codebase.
- 030-001-014: Begin work on FAISS indexing and searching.
- 023-002-011: Finish refactoring allpress.db.models
- 023-001-010: Fix primary key issue on article saves.
- 010-003-003: Bug test scraper
- 010-004-004: Bug test article detector

## Completed

- 030-003-016: Fixed bug 030-005 
- 023-004-013: Change rhetorical embedding and semantic embedding calculations. (0.3.0a)
- 023-003-012: Fix article detection heuristics, as it currently has too many false positives. (0.3.0a)
- 020-001-007: Begin work on semantic autoencoder (0.2.2a)
- 022-001-008: Finish io for DB. Includes; creating tables, writing to tables, reading from tables for page model. (0.2.2a)
- 010-005-005: Write documentation for Scraper (0.1.1a)
- 010-006-006: Implement error handling for Scraper and Article Detector (0.1.1a)
- 010-001-001: Finish basic implementation of Scraper (0.1.0a)
- 010-002-002: Finish article detector (0.1.0a)


## Bugs

- 040-008: Using `.to(device)` with torch_directml causes a "Cannot set version counter for inference tensor error"
- 040-007: Some websites return empty list of embeddings.
- 030-006: Thread pool executor bug at line 73 `_execute_pool()`, TypeError with comparison operator `<=`.
- 030-004: Scraper fails to redirect away from pages on the same website but different subdomain.
- 023-003: AttributeErrors on saving to database.
- 022-002: Primary key issue where duplicate articles are saved to the database. 
- 011-001: On second iteration, the starting domain appears in the `new_found_urls` list.


## Abandoned