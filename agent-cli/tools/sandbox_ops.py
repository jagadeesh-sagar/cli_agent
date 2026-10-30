import subprocess,os
from pathlib import Path
from .file_ops import get_project_path


def cleanup():

    subprocess.run(["docker", "rm", "-f", "agent-proxy", "agent-sandbox"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["docker","network","rm","agent-internal-net","agent-proxy-net"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    
def start_sandbox(container_name='agent-sandbox'):
    '''
     =>here we are doing simple think we set up a proxy container(open source docker) that has a internet connection
     =>there is a config file which we mounted on to that container which has ACL(access control list ) to allow only certain ip addresses
    '''
    cleanup()

    squid_conf_path=Path(__file__).parent/'squid.conf'
    if not os.path.isfile(squid_conf_path):
        raise FileNotFoundError(f"Missing configuration file at: {squid_conf_path}")
    
    subprocess.run(["docker","network","create","--internal","agent-internal-net"],check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["docker","network","create","agent-proxy-net"],check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run([
        "docker", "run", "-d", "--name", "agent-proxy",
        "--network", "agent-proxy-net",
        "-v", f"/home/jaggu/Desktop/cli_agent/agent-cli/tools/squid.conf:/etc/squid/squid.conf",
        "sameersbn/squid",  #  sameersbn famous old squid proxy (there other opwn proxies too)
    ],check=True)

    subprocess.run(["docker","network","connect","agent-internal-net","agent-proxy"])

    subprocess.run([
    "docker", "run", "-d", "--name", container_name,
    "--network", "agent-internal-net",
    "-e", "HTTP_PROXY=http://agent-proxy:3128",
    "-e", "HTTPS_PROXY=http://agent-proxy:3128",
    "-e", "http_proxy=http://agent-proxy:3128",
    "-e", "https_proxy=http://agent-proxy:3128",
    "-e", "NO_PROXY=localhost,127.0.0.1",
    "--volume", f"{get_project_path()}:/workspace",
    "--workdir", "/workspace",
    "agent-sandbox",
    "sleep", "infinity",
    ],check=True)

    # Inject bash wrapper for git guardrails
    wrapper_script = """cat << 'EOF' > /usr/local/bin/git
#!/bin/sh
for arg in "$@"; do
    if [ "$arg" = "--force" ] || [ "$arg" = "-f" ]; then
        echo "ERROR: --force is disabled in this environment for safety." >&2
        exit 1
    fi
done
exec /usr/bin/git "$@"
EOF
chmod +x /usr/local/bin/git
"""
    subprocess.run(["docker", "exec", container_name, "sh", "-c", wrapper_script], check=True)


def bash(command: str, container_name='agent-sandbox', timeout=60) -> dict:

    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output=result.stdout
        if result.stderr:
            output+=f'\n[stderr]\n{result.stderr}'
        output+=f'\n[exit_code: {result.returncode}]'

        return output or f"(no output)\n[exit_code: {result.returncode}]"
    
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {timeout}s\n[exit_code: 124]"
    except Exception as e:
        return f"TOOL_ERROR: {e}\n[exit_code: 1]"