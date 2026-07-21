from pathlib import Path
import subprocess


def list_skills()->str:
    '''
    used to load all skills names to the agent .. 
    helps in reducing the context ->token->cheap->compared to system prompt
    '''

    skills_name = []
    # parent = tools/, parent.parent = agent-cli/
    skills_dir = Path(__file__).parent.parent / "skills"

    if not skills_dir.exists():
        return "No skills loaded."

    for path in skills_dir.glob("*/SKILL.md"):
        skills_name.append(path.parent.name)  

    return "\n".join(skills_name)

def load_skill(name: str) -> str:
    '''returns the content of the SKILL.md file'''
    skills_dir = Path(__file__).parent.parent / "skills"  # agent-cli/skills/
    content_path = skills_dir / name / "SKILL.md"
    
    if not content_path.exists():
        return f"Error: Skill '{name}' not found."
        
    return content_path.read_text()




