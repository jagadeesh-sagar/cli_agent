from pathlib import Path

import chromadb

class VectorIndex:
    def __init__(self,index_dir:Path):
        self.client=chromadb.PersistentClient(path=str(index_dir/"chroma"))
        self.col=self.client.get_or_create_collection("code_chunks")

    def delete_file(self,path:str):
        self.col.delete(where={"path":path})

    def add(self,ids,embeddings,metadatas):
        for i in range(0,len(ids),256):
            self.col.upsert(ids=ids[i:i+256],
                          embeddings=embeddings[i:i+256],
                            metadatas=metadatas[i:i+256]
                                )

    def query(self,embedding,k:int)-> list[str]:
        n=self.col.count()
        if n==0:
            return []
        res=self.col.query(query_embeddings=[embedding],n_results=min(k,n),include=['distances'])
        return res["ids"][0]

    