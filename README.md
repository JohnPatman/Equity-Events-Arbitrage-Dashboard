Live app: https://equity-events-arbitrage-dashboard-byv5jedymv77prgu9fg3jz.streamlit.app

A Streamlit-based financial analytics platform focused on dividend forecasting, FX arbitrage, ADR mispricing, earnings behaviour, and global equity valuation.

Overview:

-- This project is an interactive dashboard designed to identify pricing inefficiencies across global equity markets, combining tools commonly used in corporate actions, trading desks, quantitative research, and investment analysis.

-- It is designed for corporate actions professionals, trading support and equity finance desks, and quantitatively minded investors analysing event-driven inefficiencies.

-- The dashboard integrates live market data, company-published terms, and deterministic financial models. Strategy simulators (e.g. Synthetic SPY) are analytical tools intended to stress-test structure, margin usage, and regime sensitivity, not to provide trading recommendations or predict returns.

Features:

1. Upcoming UK Dividend Events
Fetches company investor-relations announcements and builds a forward dividend calendar for major UK stocks. Dates and declared amounts are standardised, and uncertainty is flagged where appropriate.

2. Dividend Growth Model
Analyses fifteen years of dividend history. Highlights annual increases and decreases to show long-term payout behaviour and stability.

3. Currency Arbitrage
Evaluates dividend currency election opportunities by comparing the company’s published FX rate with live market FX. Includes borrow-arbitrage modelling, forward-FX hedging, and a FX Override & Scenario Test.

4. ADR vs Local Share Arbitrage
Normalises local share prices into ADR terms using FX and conversion ratios. Identifies deviations between ADR and local listings and highlights potential arbitrage opportunities.

5. Earnings Intelligence
Examines historical earnings surprises, beat rates, and volatility. Displays recent reported quarters and visualises surprise behaviour to support pre-earnings analysis and strategy design.

6. Scrip Dividend Arbitrage
Models the value of cash versus scrip elections using current market prices and the company’s scrip issue price. Provides optimal election recommendations, including scenarios where a lender mandates the election.

7. Global Equity Valuation Model
Compares valuation metrics and performance across countries using dividend yield, P/E, forward P/E, price-to-book, and multi-period returns. Includes a scoring model and a heat-mapped valuation table with CSV export.

8. Country Exposure with a Mix of Funds
Blends multiple fund allocations to generate a full country-level portfolio exposure. Scrapes geographic weights from HL factsheets, applies user-defined allocation percentages, aggregates exposures, assigns market classifications (Developed, Emerging, Frontier), and visualises results through ranked tables, bar charts, and classification breakdowns.

9. Macro Signals Dashboard aggregates key macroeconomic indicators to assess market conditions. Includes US Treasury yield curve analysis (3M–30Y), US vs UK CPI trends with selectable history windows, real (inflation-adjusted) yields, and a combined macro regime score incorporating curve slope, inflation momentum, and monetary-tightness signals.

10. Synthetic SPY Strategy Simulator
Models a capital-efficient synthetic long S&P 500 strategy using a call–put structure. Evaluates margin usage, funding carry, drawdowns, and survivability across market regimes, with equal-cash comparisons against buy-and-hold SPY, SSO, and UPRO including equity curves and annual return breakdowns.

Technical Stack: 

Python -- Streamlit, pandas, NumPy, Altair, Plotly, yfinance, Requests, BeautifulSoup4, lxml, matplotlib.

Data Sources:

- Company IR websites
- Market FX feeds
- Yahoo Finance
- MSCI datasets

Skills Demonstrated:

1. Financial modelling: 

Dividend forecasting, FX parity analysis, ADR conversion, earnings surprise analysis, valuation modelling.

2. Software engineering: 

Modular architecture, data scraping, API integration, input validation, state management, and production deployment using Streamlit Cloud.

3. Quantitative analysis:

Arbitrage logic, forward-FX modelling, ratio normalisation, time-series interpretation, and structured data pipelines.


Created by: John Patman