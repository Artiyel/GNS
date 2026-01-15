from pathlib import Path
import shutil

def copy_file(src: Path, dst: Path):
    shutil.copy2(src, dst) 
    print(f"Copied {src} to {dst}")


dynamips = Path("test_drag/project-files/dynamips")

config_folders = []
for file in dynamips.glob("*"):
    
    if file.is_dir():
        config_folders.append(file)

for folder in config_folders:
    config_folder = folder / "configs"

    for config_file in config_folder.glob("*.cfg"):
        router_number = config_file.name.split("_", 1)[0][1:]

    src = Path(f"config/R{router_number}_i{router_number}_startup-config.cfg")
    dst = Path(f"test_drag/project-files/dynamips/{folder.name}/configs/{config_file.name}")
    copy_file(src, dst)



