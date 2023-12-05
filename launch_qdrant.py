import subprocess

cmd = "docker pull qdrant/qdrant"
subprocess.call(cmd, shell=True)

cmd = "docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant"
subprocess.call(cmd, shell=True)