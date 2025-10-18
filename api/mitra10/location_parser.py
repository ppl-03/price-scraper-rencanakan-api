from bs4 import BeautifulSoup

class Mitra10LocationParser:
    @staticmethod
    def parse(html: str):
        soup = BeautifulSoup(html, "html.parser")
        locations = []
        for span in soup.select("div[role='presentation'] li span"):
            text = span.get_text(strip=True)
            if text:
                # Remove "MITRA10 " prefix if it exists
                if text.startswith("MITRA10 "):
                    text = text[8:]  # Remove "MITRA10 " (8 characters)
                locations.append(text)
        return locations
