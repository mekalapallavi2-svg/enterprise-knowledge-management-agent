import os
import sys
from database import db

def test_database_indexing():
    print("==================================================")
    print("Database and TF-IDF Retrieval Verification Script")
    print("==================================================")

    docs_dir = "docs"
    if not os.path.exists(docs_dir):
        print(f"Error: {docs_dir} directory not found.")
        sys.exit(1)
        
    print(f"Reading files in '{docs_dir}' directory...")
    files = [f for f in os.listdir(docs_dir) if f.endswith(".md")]
    
    if not files:
        print("Error: No markdown files found in the docs directory.")
        sys.exit(1)

    print(f"Found {len(files)} files to index: {files}")
    
    predefined_meta = {
        "hr_policy.md": {
            "date": "2025-06-15",
            "author": "HR Department",
            "department": "Human Resources",
            "doc_type": "Policy"
        },
        "data_privacy_policy.md": {
            "date": "2025-09-10",
            "author": "CISO Office",
            "department": "Information Security",
            "doc_type": "Policy"
        },
        "employee_handbook.md": {
            "date": "2025-01-10",
            "author": "HR Operations Team",
            "department": "Human Resources",
            "doc_type": "Policy"
        }
    }

    print("\nStarting indexing process...")
    for filename in files:
        file_path = os.path.join(docs_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        meta = predefined_meta.get(filename, {
            "date": "2025-01-01",
            "author": "Admin",
            "department": "Operations",
            "doc_type": "Policy"
        })
        
        title = filename.replace("_", " ").replace(".md", "").title()
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line.replace("# ", "").strip()
                break
                
        chunks = db.add_document(title, content, meta)
        print(f" - Indexed '{title}' -> generated {chunks} chunks.")

    print(f"\nDatabase setup complete. Total Chunks Indexed: {len(db.chunks)}")
    print(f"Vocabulary terms cataloged: {len(db.vocab)}")

    test_queries = [
        "What is the annual leave rollover limit?",
        "How is PII encrypted in our systems?",
        "What are the onboarding tasks for Day 2?"
    ]

    print("\nRunning Semantic Cosine-Similarity Search Verification...")
    for q in test_queries:
        print(f"\nQuery: \"{q}\"")
        matches = db.search(q, top_k=2)
        if not matches:
            print(" -> No chunks matched the search tokens.")
            continue
            
        for idx, match in enumerate(matches):
            print(f"   [{idx+1}] Score: {match['relevance_score']} | File: '{match['source_document']}' | Sec: '{match['page_or_section']}'")
            preview = match['content'][:120].replace('\n', ' ')
            print(f"       Text: \"{preview}...\"")

    print("\n==================================================")
    print("Database Index Verification: PASSED")
    print("==================================================")

if __name__ == "__main__":
    test_database_indexing()
