import chromadb
from config import cfg 
from sentence_transformers import SentenceTransformer
from pathlib import Path

# model=SentenceTransformer("all-MiniLM-L6-v2")
client=chromadb.PersistentClient(path=cfg.vector_db_path)
collection=client.get_or_create_collection('vectors')

avoid_dirs= {"node_modules", ".git", "venv", "__pycache__"}
avoid_extensions={".log", ".tmp", ".exe", ".bak",".yaml",".json",".pyc","dockerfile",'.env','.db','.md'}

def scan_directory(project_path:Path)->any:

    for path in Path(project_path).iterdir():
        # skip the specified folders completely
        if path.is_dir() and path.name in avoid_dirs:
            continue

        if path.is_dir():
            # recusrsive into the folder depth
            yield from scan_directory(path)
        else:
            if path.suffix.lower() in avoid_extensions or path.name.lower() in avoid_extensions:
                continue
            else:

             yield path

def index_project(project_path:Path,model)->None:
    for valid_file in scan_directory(project_path):
        try:
            content=valid_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        chunks= [content[i:i+2000] for i in range(0,len(content),2000)]
        for i , chunk in enumerate(chunks):
            collection.upsert(
                ids=[f'{valid_file}:{i}'],
                documents=[chunk],
                embeddings=[model.encode(chunk).tolist()],
                metadatas=[{"file":str(valid_file),"chunk":i}]
            )

def semantic_search(query:str,model)->list:

    query_embedding=model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1
    )

    print(results["documents"])
    print(results["metadatas"])

    return results["documents"]+results["metadatas"]
