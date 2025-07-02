import allpress

a = allpress.net.scrape.Scraper()
articles = []
for soupdict in a.scrape('https://apnews.com'):
    for content in soupdict.values():
        article = allpress.nlp.processors.Article(content[1], content[0]) # fix magic numbers later
        print('hi')