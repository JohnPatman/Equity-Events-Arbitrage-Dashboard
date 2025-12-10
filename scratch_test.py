from modules.portfolio.hl_scraper import scrape_country_weights

url = "https://www.hl.co.uk/funds/fund-discounts,-prices--and--factsheets/search-results/f/fidelity-index-world-class-p-accumulation"
df = scrape_country_weights(url)
print(df)

