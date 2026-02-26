import os
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser
from models import Alert

INDEX_DIR = "indexdir"

def get_schema():
    return Schema(title=TEXT(stored=True), content=TEXT, path=ID(stored=True), category=TEXT(stored=True))

def init_index():
    if not os.path.exists(INDEX_DIR):
        os.mkdir(INDEX_DIR)
        create_in(INDEX_DIR, get_schema())

def index_alert(alert):
    if not os.path.exists(INDEX_DIR):
        init_index()
    
    ix = open_dir(INDEX_DIR)
    writer = ix.writer()
    writer.add_document(
        title=alert.title,
        content=alert.summary if alert.summary else "",
        path=str(alert.id),
        category=alert.category if alert.category else "Uncategorized"
    )
    writer.commit()

def search_alerts(query_str):
    if not os.path.exists(INDEX_DIR):
        return []

    ix = open_dir(INDEX_DIR)
    results_list = []
    
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(query_str)
        results = searcher.search(query, limit=20)
        for r in results:
            results_list.append({
                "id": r["path"],
                "title": r["title"],
                "category": r["category"]
            })
    return results_list

def rebuild_index(db_session):
    init_index()
    alerts = db_session.query(Alert).all()
    ix = open_dir(INDEX_DIR)
    writer = ix.writer()
    for alert in alerts:
        writer.add_document(
            title=alert.title,
            content=alert.summary if alert.summary else "",
            path=str(alert.id),
            category=alert.category if alert.category else "Uncategorized"
        )
    writer.commit()
    print(f"Index rebuilt with {len(alerts)} documents.")
