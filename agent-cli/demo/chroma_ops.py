import chromadb
# from ..config import cfg 
from sentence_transformers import SentenceTransformer
from pathlib import Path

model=SentenceTransformer("all-MiniLM-L6-v2")
client=chromadb.PersistentClient(path='/home/jaggu/Desktop/cli_agent/agent-cli/memory/')
collection=client.get_or_create_collection('vectors')

c=10
while c!=-1:
    query = "sns topic "

    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=1
    )

    print(results["documents"])
    print(results["metadatas"])
    
CODE_EXTENSIONS = {
    ".py", ".js",".ts",".jsx",".tsx",".java",".c",".cpp",".h",".hpp",".go",".rs",".rb",
    ".php", ".html", ".css", ".scss", ".sql", ".sh", ".txt",
}
AVOID_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    ".idea",
    ".vscode",
}


def scan_directory(project_path:Path):

    for path in Path(project_path).iterdir():
        # skip the specified folders completely
        if path.is_dir():

            if path.name in AVOID_DIRS :
                continue

            yield from scan_directory(path)
        else:
            if path.suffix.lower() not in CODE_EXTENSIONS:
                continue
            yield path

def index_project(project_path:Path):

    skipped=0
    indexed=0

    for valid_file in scan_directory(project_path):

        try:
           content=valid_file.read_text()
        except (UnicodeDecodeError,OSError) as e:

            print(f"Skipping {valid_file}: {e}")
            skipped += 1
            continue
        if not content.strip():
            continue

        chunks= [content[i:i+2000] for i in range(0,len(content),2000)]

        for i , chunk in enumerate(chunks):
            embedding=model.encode(chunk).tolist()

            collection.upsert(
                ids=[f'{valid_file}:{i}'],
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{"file":str(valid_file),"chunk":i}]
            )
        indexed+=1
    
    print(f"Indexed chunks: {indexed}")
    print(f"Skipped files: {skipped}")
