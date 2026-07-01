# Dockerising the Knowledge Base Tool

Files in this folder:

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the web-server image (Python 3.12-slim + Uvicorn). |
| `requirements.txt` | Web-only deps (no pyinstaller/pystray/pillow/typer). |
| `config.docker.yaml` | Container config — all data dirs point at `/data`. |
| `docker-compose.yml` | One-command build+run with a persistent volume. |

> **Build context = the project root.** The Dockerfile copies `app/`,
> `templates/`, `static/` from the repo root, so you build from there and point
> `-f` at this Dockerfile.

---

## Option A — plain Docker

### 1. Build
From the **project root** (`knowledge_base_tool/`):

```bash
docker build -f dockerise/Dockerfile -t kb-tool .
```

### 2. Run
```bash
docker run -d --name kb-tool -p 5050:5050 -v kb-data:/data kb-tool
```
- `-p 5050:5050` → app at **http://localhost:5050**
- `-v kb-data:/data` → all content (posts, notes, books, music, toeic, images,
  search index) persists in the named volume `kb-data`.

### 3. Use / manage
```bash
docker logs -f kb-tool        # follow logs
docker stop kb-tool           # stop
docker start kb-tool          # start again (data persists)
docker rm -f kb-tool          # remove container (volume kb-data survives)
```

---

## Option B — docker compose

From the **project root**:

```bash
docker compose -f dockerise/docker-compose.yml up --build -d
# open http://localhost:5050
docker compose -f dockerise/docker-compose.yml logs -f
docker compose -f dockerise/docker-compose.yml down       # stop (volume kept)
```

---

## Updating after a feature/code change (without losing data)

Your content lives in the **`/data` volume**, which is separate from the image.
Rebuilding the image and recreating the container does **not** touch the volume,
so all your posts/notes/music/books/etc. survive.

### Plain Docker
```bash
# 1. rebuild the image with the new code (from the project root)
docker build -f dockerise/Dockerfile -t kb-tool .

# 2. replace the container — the kb-data volume is reused, data is kept
docker rm -f kb-tool
docker run -d --name kb-tool -p 5050:5050 -v kb-data:/data kb-tool
```

### docker compose (simpler)
```bash
docker compose -f dockerise/docker-compose.yml up --build -d
```
`up --build` rebuilds the image and recreates the container in place; the
`kb-data` volume persists.

### ⚠️ The only things that delete data
- `docker volume rm kb-data`
- `docker compose ... down -v`   ← the `-v` flag wipes volumes
- removing/renaming the volume, or pointing `-v` at a different name

Plain `docker rm -f kb-tool`, `docker stop/start`, and `docker compose down`
(without `-v`) all **keep** the volume.

### Recommended: back up before updating
```bash
# snapshot the volume to a tarball in the current dir
docker run --rm -v kb-data:/data -v "$(pwd)":/backup alpine \
  tar czf /backup/kb-data-backup.tgz -C /data .

# restore it later if needed
docker run --rm -v kb-data:/data -v "$(pwd)":/backup alpine \
  sh -c "cd /data && tar xzf /backup/kb-data-backup.tgz"
```
> If you used **bind mounts** instead of the named volume (see below), your data
> is just files in your repo folders — back them up by copying those folders.
> The search index (`/data/.kb/search.db`) is always rebuildable and safe to lose.

> **Verified:** created a note → `docker build --no-cache` → `docker rm -f` +
> re-`run` with the same `-v kb-data:/data` → the note was still there.

## Using your existing local content

By default the container starts with an empty `/data` volume. To serve the
markdown you already have in the repo, bind-mount those folders instead of the
named volume:

```bash
docker run -d --name kb-tool -p 5050:5050 \
  -v "$(pwd)/posts:/data/posts" \
  -v "$(pwd)/notes:/data/notes" \
  -v "$(pwd)/books:/data/books" \
  -v "$(pwd)/music:/data/music" \
  -v "$(pwd)/toeic:/data/toeic" \
  -v "$(pwd)/img:/data/img" \
  kb-tool
```
(Or uncomment the bind-mount lines in `docker-compose.yml`.)

---

## How it works / notes

- **Why a separate config:** `config.docker.yaml` sets every data path to an
  absolute `/data/...`. The app resolves data dirs as `base_dir / configured`,
  and an absolute path overrides the base — so all content lands in `/data`,
  which is the one volume you mount. The dirs are auto-created on startup.
- **No tray/CLI in the image:** the container runs `uvicorn app.main:app`
  directly on `0.0.0.0:5050`; `pystray`/`pillow`/`pyinstaller`/`typer` are
  intentionally excluded to keep the image small.
- **Audio** is served at `/audio/<slug>.mp3` and images at `/img/<hash>` from
  `/data` — both persist in the volume.
- **Change the port:** map a different host port, e.g. `-p 8080:5050`, then open
  `http://localhost:8080`. (Container port stays 5050.)

## Verified

Built and run in this environment (Docker 29.4.1):
`GET /`, `/posts`, `/notes`, `/favicon.ico` → **200**; a note created in the
running container was written to `/data/notes/` and **survived a container
restart** via the `kb-data` volume.
