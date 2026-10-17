import asyncio
from playwright.async_api import async_playwright

URL = "https://equity-events-arbitrage-dashboard.streamlit.app/"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print(f"Visiting {URL}")
            await page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
            await page.wait_for_timeout(5000)

            # Click the wake-up button if the app is asleep
            wake_btn = page.get_by_role("button", name="Yes, get this app back up!")
            if await wake_btn.count() > 0:
                print("App is asleep — clicking wake button...")
                await wake_btn.click()
                await page.wait_for_timeout(60_000)  # give it time to start
                print("Wake requested.")
            else:
                print("App is already awake.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
