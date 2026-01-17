import argparse
import requests
import sqlite3
import pandas as pd
from datetime import datetime

API_KEY = "YOUR_NEWSAPI_KEY_HERE"  
DB_NAME = "news_data.db"


class NewsAggregator:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                author TEXT,
                title TEXT,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT
            )
        """)
        self.conn.commit()

    def fetch_from_api(self, query="technology"):
        url = f"https://newsapi.org/v2/everything?q={query}&apiKey={API_KEY}"

        try:
            response = requests.get(url)
            data = response.json()

            if data.get("status") != "ok":
                print("Error:", data.get("message"))
                self._insert_dummy_data(query)
                return

            articles = data.get("articles", [])
            count = 0

            for art in articles:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO news
                    (source, author, title, url, published_at, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    art["source"]["name"],
                    art.get("author", "Unknown"),
                    art["title"],
                    art["url"],
                    art["publishedAt"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                if self.cursor.rowcount > 0:
                    count += 1

            self.conn.commit()
            print(f"Success! Added {count} new unique articles for '{query}'.")

        except Exception as e:
            print("Fetch error:", e)
            self._insert_dummy_data(query)

    def _insert_dummy_data(self, query):
        print(f"Inserting dummy data for query '{query}' due to API error.")
        dummy_articles = [
            {
                "source": {"name": "Dummy News"},
                "author": "AI Assistant",
                "title": f"Dummy Article 1 about {query}",
                "url": f"http://dummy.news.com/article1_{query}_{datetime.now().timestamp()}",
                "publishedAt": datetime.now().isoformat()
            },
            {
                "source": {"name": "Fake Press"},
                "author": "Bot Reporter",
                "title": f"Another Dummy Headline on {query}",
                "url": f"http://fake.press.org/headline2_{query}_{datetime.now().timestamp()}",
                "publishedAt": datetime.now().isoformat()
            }
        ]
        count = 0
        for art in dummy_articles:
            self.cursor.execute("""
                INSERT OR IGNORE INTO news
                (source, author, title, url, published_at, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                art["source"]["name"],
                art.get("author", "Unknown"),
                art["title"],
                art["url"],
                art["publishedAt"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            if self.cursor.rowcount > 0:
                count += 1
        self.conn.commit()
        print(f"Added {count} dummy articles for '{query}'.")

    def list_news(self, keyword=None, source=None, from_date=None, to_date=None):
        query = "SELECT id, title, source, published_at FROM news WHERE 1=1"
        params = []

        if keyword:
            query += " AND title LIKE ?"
            params.append(f"%{keyword}%")

        if source:
            query += " AND source LIKE ?"
            params.append(f"%{source}%")

        if from_date:
            query += " AND date(published_at) >= date(?)"
            params.append(from_date)

        if to_date:
            query += " AND date(published_at) <= date(?)"
            params.append(to_date)

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()

        if not rows:
            print("No articles found.")
            return

        print(f"\nFound {len(rows)} articles")
        print("-" * 80)
        print(f"{'ID':<5} | {'Source':<20} | {'Title'}")
        print("-" * 80)

        for row in rows:
            title = row[1][:55] + "..." if len(row[1]) > 55 else row[1]
            print(f"{row[0]:<5} | {row[2]:<20} | {title}")

        print("-" * 80)

    def export_data(self, file_format):
        df = pd.read_sql_query("SELECT * FROM news", self.conn)

        if df.empty:
            print("No data to export.")
            return

        filename = f"news_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if file_format == "csv":
            df.to_csv(f"{filename}.csv", index=False)
            print(f"Exported to {filename}.csv")

        elif file_format == "excel":
            df.to_excel(f"{filename}.xlsx", index=False)
            print(f"Exported to {filename}.xlsx")

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="News Aggregator CLI")
    subparsers = parser.add_subparsers(dest="command")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch news")
    fetch_parser.add_argument("--query", default="technology")

    list_parser = subparsers.add_parser("list", help="List news")
    list_parser.add_argument("--keyword")
    list_parser.add_argument("--source")
    list_parser.add_argument("--from-date", help="YYYY-MM-DD")
    list_parser.add_argument("--to-date", help="YYYY-MM-DD")

    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("format", choices=["csv", "excel"])

    args = parser.parse_args([]) 
    app = NewsAggregator()

    if args.command == "fetch":
        app.fetch_from_api(args.query)

    elif args.command == "list":
        app.list_news(
            keyword=args.keyword,
            source=args.source,
            from_date=args.from_date,
            to_date=args.to_date
        )

    elif args.command == "export":
        app.export_data(args.format)

    else:
        parser.print_help()

    app.close()
