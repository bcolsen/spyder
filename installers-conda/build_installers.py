"""
Create Spyder installers using `constructor`.

It creates a `construct.yaml` file with the needed settings
and then runs `constructor`.

Some environment variables we use:

CONSTRUCTOR_TARGET_PLATFORM:
    conda-style platform (as in `platform` in `conda info -a` output)
CONSTRUCTOR_CONDA_EXE:
    when the target platform is not the same as the host, constructor
    needs a path to a conda-standalone (or micromamba) executable for
    that platform. needs to be provided in this env var in that case!
CONSTRUCTOR_SIGNING_CERTIFICATE:
    Path to PFX certificate to sign the EXE installer on Windows
"""

import json
import os
import platform
import re
import sys
import zipfile
from argparse import ArgumentParser
from datetime import timedelta
from distutils.spawn import find_executable
from functools import partial
from logging import getLogger
from pathlib import Path
from ruamel.yaml import YAML
from subprocess import check_call
from textwrap import dedent, indent
from time import time

from build_conda_pkgs import HERE, DIST, RESOURCES, SPECS, h, get_version

logger = getLogger('BuildInstallers')
logger.addHandler(h)
logger.setLevel('INFO')

APP = "Spyder"
SPYREPO = HERE.parent
WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
TARGET_PLATFORM = os.environ.get("CONSTRUCTOR_TARGET_PLATFORM")
if TARGET_PLATFORM == "osx-arm64":
    ARCH = "arm64"
else:
    ARCH = (platform.machine() or "generic").lower().replace("amd64", "x86_64")
PY_VER = f"{sys.version_info.major}.{sys.version_info.minor}"
if WINDOWS:
    EXT, OS = "exe", "Windows"
elif LINUX:
    EXT, OS = "sh", "Linux"
elif MACOS:
    EXT, OS = "pkg", "macOS"
else:
    raise RuntimeError(f"Unrecognized OS: {sys.platform}")

# ---- Parse arguments
p = ArgumentParser()
p.add_argument(
    "--no-local", action="store_true",
    help="Do not use local conda packages"
)
p.add_argument(
    "--debug", action="store_true",
    help="Do not delete build files"
)
p.add_argument(
    "--arch", action="store_true",
    help="Print machine architecture tag and exit.",
)
p.add_argument(
    "--ext", action="store_true",
    help="Print installer extension for this platform and exit.",
)
p.add_argument(
    "--artifact-name", action="store_true",
    help="Print computed artifact name and exit.",
)
p.add_argument(
    "--extra-specs", nargs="+", default=[],
    help="One or more extra conda specs to add to the installer",
)
p.add_argument(
    "--licenses", action="store_true",
    help="Post-process licenses AFTER having built the installer. "
    "This must be run as a separate step.",
)
p.add_argument(
    "--images", action="store_true",
    help="Generate background images from the logo (test only)",
)
p.add_argument(
    "--cert-id", default=None,
    help="Apple Developer ID Application certificate common name."
)
args = p.parse_args()

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
indent4 = partial(indent, prefix="    ")

SPYVER = get_version(SPYREPO).strip().split("+")[0]

specs = {"spyder": "=" + SPYVER}
try:
    logger.info(f"Reading specs from {SPECS}...")
    _specs = yaml.load(SPECS.read_text())
    specs.update({k: "=" + v for k, v in _specs.items()})
except Exception:
    logger.info(f"Did not read specs from {SPECS}")

for spec in args.extra_specs:
    k, *v = re.split('([<>= ]+)', spec)
    specs[k] = "".join(v).strip()
    if k == "spyder":
        SPYVER = v[-1]

OUTPUT_FILE = DIST / f"{APP}-{SPYVER}-{OS}-{ARCH}.{EXT}"
INSTALLER_DEFAULT_PATH_STEM = f"{APP}-{SPYVER}"


def _generate_background_images(installer_type):
    """Requires pillow"""
    if installer_type == "sh":
        # shell installers are text-based, no graphics
        return

    from PIL import Image

    logo_path = SPYREPO / "img_src" / "spyder.png"
    logo = Image.open(logo_path, "r")

    if installer_type in ("exe", "all"):
        sidebar = Image.new("RGBA", (164, 314), (0, 0, 0, 0))
        sidebar.paste(logo.resize((101, 101)), (32, 180))
        output = DIST / "spyder_164x314.png"
        sidebar.save(output, format="png")

        banner = Image.new("RGBA", (150, 57), (0, 0, 0, 0))
        banner.paste(logo.resize((44, 44)), (8, 6))
        output = DIST / "spyder_150x57.png"
        banner.save(output, format="png")

    if installer_type in ("pkg", "all"):
        _logo = Image.new("RGBA", logo.size, "WHITE")
        _logo.paste(logo, mask=logo)
        background = Image.new("RGBA", (1227, 600), (0, 0, 0, 0))
        background.paste(_logo.resize((148, 148)), (95, 418))
        output = DIST / "spyder_1227x600.png"
        background.save(output, format="png")


def _get_condarc():
    # we need defaults for tensorflow and others on windows only
    defaults = "- defaults" if WINDOWS else ""
    prompt = "[spyder]({default_env}) "
    contents = dedent(
        f"""
        channels:  #!final
          - spyder-ide
          - conda-forge
          {defaults}
        repodata_fns:  #!final
          - repodata.json
        auto_update_conda: false  #!final
        notify_outdated_conda: false  #!final
        channel_priority: strict  #!final
        env_prompt: '{prompt}'  #! final
        """
    )
    # the undocumented #!final comment is explained here
    # https://www.anaconda.com/blog/conda-configuration-engine-power-users
    file = DIST / "condarc"
    file.write_text(contents)

    return str(file)


def _definitions():
    condarc = _get_condarc()
    definitions = {
        "name": APP,
        "company": "Spyder-IDE",
        "reverse_domain_identifier": "org.spyder-ide.Spyder",
        "version": SPYVER,
        "channels": [
            "napari/label/bundle_tools",
            "spyder-ide",
            "conda-forge",
        ],
        "conda_default_channels": ["conda-forge"],
        "specs": [
            "python",
            "conda",
            "mamba",
            "pip",
        ],
        "installer_filename": OUTPUT_FILE.name,
        "initialize_by_default": False,
        "license_file": str(RESOURCES / "bundle_license.rtf"),
        "extra_envs": {
            f"spyder-{SPYVER}": {
                "specs": [k + v for k, v in specs.items()],
            },
        },
        "menu_packages": [
            "spyder",
        ],
        "extra_files": {
            str(RESOURCES / "bundle_readme.md"): "README.txt",
            condarc: ".condarc",
        },
    }
    if not args.no_local:
        definitions["channels"].insert(0, "local")

    if LINUX:
        definitions["default_prefix"] = os.path.join(
            "$HOME", ".local", INSTALLER_DEFAULT_PATH_STEM
        )
        definitions["license_file"] = str(SPYREPO / "LICENSE.txt")
        definitions["installer_type"] = "sh"

    if MACOS:
        welcome_text_tmpl = \
            (RESOURCES / "osx_pkg_welcome.rtf.tmpl").read_text()
        welcome_file = DIST / "osx_pkg_welcome.rtf"
        welcome_file.write_text(
            welcome_text_tmpl.replace("__VERSION__", SPYVER))

        # These two options control the default install location:
        # ~/<default_location_pkg>/<pkg_name>
        definitions.update(
            {
                "pkg_name": INSTALLER_DEFAULT_PATH_STEM,
                "default_location_pkg": "Library",
                "installer_type": "pkg",
                "welcome_image": str(DIST / "spyder_1227x600.png"),
                "welcome_file": str(welcome_file),
                "conclusion_text": "",
                "readme_text": "",
                "post_install": str(RESOURCES / "post-install.sh"),
            }
        )
        if args.cert_id:
            definitions["signing_identity_name"] = args.cert_id
            definitions["notarization_identity_name"] = args.cert_id

    if WINDOWS:
        definitions["conda_default_channels"].append("defaults")
        definitions.update(
            {
                "welcome_image": str(DIST / "spyder_164x314.png"),
                "header_image": str(DIST / "spyder_150x57.png"),
                "icon_image": str(DIST / "icon.ico"),
                "register_python_default": False,
                "default_prefix": os.path.join(
                    "%LOCALAPPDATA%", INSTALLER_DEFAULT_PATH_STEM
                ),
                "default_prefix_domain_user": os.path.join(
                    "%LOCALAPPDATA%", INSTALLER_DEFAULT_PATH_STEM
                ),
                "default_prefix_all_users": os.path.join(
                    "%ALLUSERSPROFILE%", INSTALLER_DEFAULT_PATH_STEM
                ),
                "check_path_length": False,
                "installer_type": "exe",
            }
        )
        signing_certificate = os.environ.get("CONSTRUCTOR_SIGNING_CERTIFICATE")
        if signing_certificate:
            definitions["signing_certificate"] = signing_certificate

    if definitions.get("welcome_image") or definitions.get("header_image"):
        _generate_background_images(definitions.get("installer_type", "all"))

    return definitions


def _constructor():
    """
    Create a temporary `construct.yaml` input file and
    run `constructor`.

    Parameters
    ----------
    version: str
        Version of `spyder` to be built. Defaults to the
        one detected by `importlib` from the source code.
    extra_specs: list of str
        Additional packages to be included in the installer.
        A list of conda spec strings (`numpy`, `python=3`, etc)
        is expected.
    """
    constructor = find_executable("constructor")
    if not constructor:
        raise RuntimeError("Constructor must be installed and in PATH.")

    definitions = _definitions()

    cmd_args = [constructor, "-v", "--output-dir", str(DIST)]
    if args.debug:
        cmd_args.append("--debug")
    conda_exe = os.environ.get("CONSTRUCTOR_CONDA_EXE")
    if TARGET_PLATFORM and conda_exe:
        cmd_args += ["--platform", TARGET_PLATFORM, "--conda-exe", conda_exe]
    cmd_args.append(str(DIST))

    env = os.environ.copy()
    env["CONDA_CHANNEL_PRIORITY"] = "strict"

    logger.info("Command: " + " ".join(cmd_args))
    logger.info("Configuration:")
    yaml.dump(definitions, sys.stdout)

    yaml.dump(definitions, DIST / "construct.yaml")

    check_call(cmd_args, env=env)


def licenses():
    info_path = DIST / "info.json"
    try:
        info = json.load(info_path)
    except FileNotFoundError:
        print(
            "!! Use `constructor --debug` to write info.json and get licenses",
            file=sys.stderr,
        )
        raise

    zipname = DIST / f"licenses.{OS}-{ARCH}.zip"
    output_zip = zipfile.ZipFile(zipname, mode="w",
                                 compression=zipfile.ZIP_DEFLATED)
    output_zip.write(info_path)
    for package_id, license_info in info["_licenses"].items():
        package_name = package_id.split("::", 1)[1]
        for license_type, license_files in license_info.items():
            for i, license_file in enumerate(license_files, 1):
                arcname = (f"{package_name}.{license_type.replace(' ', '_')}"
                           f".{i}.txt")
                output_zip.write(license_file, arcname=arcname)
    output_zip.close()
    return zipname.resolve()


def main():
    t0 = time()
    try:
        DIST.mkdir(exist_ok=True)
        _constructor()
        assert Path(OUTPUT_FILE).exists()
        logger.info(f"Created {OUTPUT_FILE}")
    finally:
        elapse = timedelta(seconds=int(time() - t0))
        logger.info(f"Build time: {elapse}")


if __name__ == "__main__":
    if args.arch:
        print(ARCH)
        sys.exit()
    if args.ext:
        print(EXT)
        sys.exit()
    if args.artifact_name:
        print(OUTPUT_FILE)
        sys.exit()
    if args.licenses:
        print(licenses())
        sys.exit()
    if args.images:
        _generate_background_images()
        sys.exit()

    main()
