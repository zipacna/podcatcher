# Podcatcher
Fork of [sebastianhutter/podcaster](https://github.com/sebastianhutter/podcaster); Mostly refactored for learning / personal use.

## Usage / Behaviour
To use
1. Install Dependencies (Python 3 required)
   1. Either directly: `pip install -r /requirements.txt`
   2. Via [Dockerfile](https://github.com/sebastianhutter/podcaster/blob/master/Dockerfile)
   3. Pipenv (or other)
2. Run `python3 main.py`

This will start the *Podcatcher*, which in turn will go through the configured Podcasts (from `podcatcher.yaml`) and download the Episodes into id-named Folders inside the *Podcasts* Folder (e.g. `podcasts/exampleID/episode1.mp3`).

## Customizations

### Added
- `DomainLanguage.dic` for use in IDE Spellchecks.
- "New" Files `main.py`, `model.py`, `podcatcher.py` and `podcatcher.yaml` are only renamed/refactored (see *Changed*)
> TODO: Wrap inside aiohttp

### Removed (currently not needed)
- `.dockerignore`
- `Dockerfile`
- `Makefile`
- `pipeline.gocd.yaml` ([GoCD](https://www.gocd.org) is not used)
- `__init__.py` (going with module instead of package approach)

### Changed
- Greatly reduced `.gitignore` (less clutter)
- Moved `appconfig.py` (with some formatting), `podcast.py`, `podcaster.py` and `podcaster.settings` (renamed to `podcatcher.yaml`) to the Top-Level of the Project.
  - `podcast.py`: Split in three files.
    - Class `Podcast` remains;
    - Class `Podcaster` was renamed to `Podcatcher` and moved into the file (`podcatcher.py`).
    - Class `SeenEntry` (along with the Constants) have been moved to `model.py`
  - `podcaster.py`: Was refactored and renamed to `main.py`
