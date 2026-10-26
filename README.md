# iheart-cli

A command-line radio player for iHeart stations, local playlists, aNONradio,
and internet-radio.com stations.

## Requirements

- Python 3.9 or newer
- VLC Media Player installed on the operating system

`python-vlc` is installed as a Python dependency, but it does not install the
VLC application itself.

## Install from GitHub

```bash
python3 -m pip install git+https://github.com/kbcortez25/iheart-cli.git
iheart --version
```

For an isolated command-line installation, use `pipx` instead:

```bash
pipx install git+https://github.com/kbcortez25/iheart-cli.git
iheart
```

## Run from a checkout

```bash
python3 -m pip install .
iheart
```

Run `iheart --help` to see the available options.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
iheart --version
```

The project uses the iHeart and internet-radio.com web endpoints directly.
Check the applicable service terms before distributing or operating it
publicly.
