# GOG Unpacker

Set of Python scripts which can be used to bulk unpack installer files for GOG games. Nothing too fancy here. But this 
does have logic to:
- Parse game details from the raw installer files (including !info.txt files if using gogrepoc to download installers).
- Download an offline copy of the GOGDB SQLite db, which is used to pull any game details which cannot be accurately 
pulled from the raw installer files.
- Determine the order game installer files should be unpacked if multiple are found for a single game.
- Generate metadata (including game version) which is landed in the destination game directory and can be later compared 
to determine whether the game needs to be reinstalled or not.


## Getting Started

### Prerequisites

- Python 3.x and virtualenv installed, e.g.:
    
```bash
pip install virtualenv
```

### Installation

1. Clone this repository to your local Windows machine.

2. Set up a virtual environment, activate it, and install requirements. To do so, open Command Prompt, browse to the 
project directory, and either run 'setup.bat' or the below commands:

```bash
python -m venv env
call env/Scripts/activate
pip install -r requirements.txt
```

3. Make a copy of '.env.dist' and 'config.jsonc.dist' (renamed to .env and config.jsonc) and update both according to your setup.

## Usage

### Command Line Arguments

| Argument | Description                                                                                                                                                                                           | Example |
| :--- |:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| :------ |
| `--config <KEY>` | Specifies the **key** of the config to process. If omitted, the script processes all configurations defined in your setup.                                                                    | `python unpack.py --config gog_service` |
| `--game <KEY>` | Specifies the **raw key** of a single game to process. If omitted, the script processes all games listed in the selected manifest(s).                                                           | `python unpack.py --game bioshock` |
| `--force` | Forces the script to **re-extract/reinstall** the game to its destination directory, even if the source files and version haven't changed.                                                           | `python unpack.py --force --game bioshock` |
| `--base-installer-only` | Limits the manifest generation for the selected game(s). Only the main base game installer will be included in the `sorted_installers` list; DLC or extra installers will be excluded. | `python unpack.py --base-installer-only` |

### Using the Script

Run the following via Command Prompt to activate the environment:

```bash
call env/Scripts/activate
```

To unpack GOG games specified by the 'gog_service' configuration within 'config.jsonc':

```bash
python unpack.py --config gog_service
```

To deactivate the environment:

```bash
deactivate
```
