import allpress

a = allpress.net.scrape.Scraper()
articles = []
for soupdict in a.scrape('https://apnews.com'):
    for article in soupdict.values(): # fix magic numbers later
        page = article[0].serialize()
        page.save()
        print('hi')
