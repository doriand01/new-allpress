import allpress

from mariadb import IntegrityError

a = allpress.net.scrape.Scraper()
articles = []
for batch in a.scrape('https://apnews.com'):
    batch.generate_embeddings()
    pages = batch.serialize()
    for page in pages: # fix magic numbers later
        try:
            page.save()
            print(f'Saved article from {page.page_url} with to the database.')
        except IntegrityError as e:
            print(f'Error saving article from {page.page_url}: {e}')

