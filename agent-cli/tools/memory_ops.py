from pathlib import Path

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
