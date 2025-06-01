#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow", "numpy", "click"]
# ///
#

import click
from PIL import Image
import os
import subprocess
import json
import numpy as np
from collections import Counter
from kmean import wkmean
import re

from colordiff import rgb, rgb_dist
import util
from util import natural_sort

MAX_FIT_ITERATIONS = 100
MAX_BINS = 1000


# Function that returns the importance of each color in 'colors'
# depending on its relative population in the image and its rgb
def calculate_importances(populations, colors):
    population_importances = populations
    color_importances = [(max(c) - min(c)) / 256 for c in colors]
    return np.array(population_importances * color_importances)


# Loads an image and extracts colors and their frequencies from an image
def get_image_colors(image_path):
    with Image.open(image_path).convert("RGB") as im:
        tally = Counter(im.getdata())

    counts = list(tally.values())
    colors = list(tally.keys())

    return np.array(counts), np.array(colors)


# Uses K-means algorithm to find the best fitting palette
# of palette_size lengths for the image
def compute_image_palette(colors, counts, palette_size, method="k++_pdf"):
    # Repeats search multiple times to find the best fit
    best_palette = None
    best_populations = None
    best_error = 10**15
    for ii in range(MAX_FIT_ITERATIONS):
        palette, populations, error = wkmean(
            palette_size, colors, weights=counts, method=method
        )
        if error < best_error:
            best_error = error
            best_palette = palette
            best_populations = populations

    importances = calculate_importances(best_populations, best_palette)

    # Sort colors in the order of importance
    inds = importances.argsort()
    palette = np.array(best_palette)[inds[::-1]]
    importances = np.array(importances)[inds[::-1]]

    return np.array(palette), np.array(importances)


# Returns num_results closest themes to the given palette
def pick_best_themes(palette, importances, num_results):
    # Load themes
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = dir_path + "/themes/colorschemes/"
    theme_names = [name[:-5] for name in os.listdir(dir_path)]
    themes = []
    for file_name in os.listdir(dir_path):
        with open(dir_path + file_name) as f:
            data = json.load(f)
        colors = [
            data["special"]["foreground"],
            data["special"]["background"],
            data["colors"]["color0"],
            data["colors"]["color1"],
            data["colors"]["color2"],
            data["colors"]["color3"],
            data["colors"]["color4"],
            data["colors"]["color5"],
            data["colors"]["color6"],
            data["colors"]["color7"],
        ]
        colors = [rgb(color) for color in colors]
        themes.append(colors)
    themes = np.array(themes, dtype=int)

    # Evaluate the score for each theme
    theme_scores = []
    for theme in themes:
        distances = []
        for palette_color in palette:
            dist = [rgb_dist(palette_color, theme_color) for theme_color in theme]
            min_dist = np.min(dist)
            distances.append(min_dist)
        distances = np.array(distances)
        score = importances.dot(distances)
        theme_scores.append(score)
    theme_scores = np.array(theme_scores)

    # Sort themes and return the first num_results themes
    inds = theme_scores.argsort()
    sorted_scores = theme_scores[inds][:num_results]
    sorted_themes = themes[inds][:num_results]
    sorted_names = np.array(theme_names)[inds][:num_results]
    return sorted_themes, sorted_scores, sorted_names


def print_palettes(palette, themes):
    L = 50
    palettes = (palette,) + tuple(themes)
    n = len(palettes)
    m = max([len(p) for p in palettes])

    def colorize(ii, palettes):
        ind_col = ii // (n * L**2)
        ind_pal = (ii % (n * L)) // L
        if ind_col < len(palettes[ind_pal]):
            return palettes[ind_pal][ind_col]
        else:
            return [255, 255, 255]

    array = np.array([colorize(ii, palettes) for ii in range(n * m * L * L)])
    array = np.reshape(array, (m * L, n * L, 3))
    array = array.astype(np.uint8)
    im = Image.fromarray(array)
    im.show()


def print_results(names, scores):
    print("    Theme", " " * 32, "Score (lower is better)")
    for ii in range(len(names)):
        print(
            str(ii) + ")" + " " * (2 - len(str(ii))),
            names[ii],
            " " * (37 - len(names[ii])),
            scores[ii],
        )


def save_current_theme():
    xrdb = subprocess.check_output("xrdb -query", shell=True)
    data = xrdb.decode()
    data = data.splitlines()
    data = [line.split(":\t") for line in data]
    colors = {}
    special = {}
    for key, value in data:
        if key[1:6] == "color":
            colors[key[1:]] = value
        elif key[1:11] == "background":
            special["background"] = value
        elif key[1:11] == "foreground":
            special["foreground"] = value
        elif key == "URxvt*cursorColor":
            special["cursor"] = value
    data = {}
    data["special"] = special
    data["colors"] = colors

    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_path = dir_path + "/revert_theme.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)
    return file_path


def install_theme(names, scores):
    backup_path = save_current_theme()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    current_theme_path = dir_path + "/current_theme"

    while True:
        print("")
        print_results(names, scores)
        n = input(
            "Enter the theme number to install, "
            + "'r' to revert to the initial theme, "
            + "or 'q' to exit:\n"
        )
        if n.isdigit():
            n = int(n)
            if n in range(len(names)):
                theme_name = names[int(n)]
                subprocess.call(f"wallust theme {theme_name}", shell=True)
                with open(current_theme_path, "w") as file:
                    file.write(theme_name)
            else:
                print("Number is outside the bounds")
        elif n == "r":
            subprocess.call("wallust theme " + backup_path, shell=True)
        elif n == "q":
            return
        else:
            print("Not a valid command")


def colors_to_bins(counts, colors, bin_size):
    tally = dict()
    for ii in range(len(colors)):
        color = colors[ii]
        count = counts[ii]
        bin = tuple((color // bin_size) * bin_size + (bin_size // 2))
        tally[bin] = tally.get(bin, 0) + count

    new_colors = list(tally.keys())
    new_counts = list(tally.values())
    return np.array(new_counts), np.array(new_colors)


def abbr(name):
    if name == "background":
        return "bg"
    if name == "foreground":
        return "fg"

    number_matches = re.findall(r"color(\d+)", name)
    if number_matches:
        return f"{name[0]}{number_matches[0]}"

    return f"{name[0]}{name[-1]}"


def printc(name, hex):
    click.echo(click.style(abbr(name).center(5), bg=util.hex_to_rgb(hex)), nl=False)


def map_gogh_theme(gogh_theme):
    special_regex = re.compile(r"^(foreground|background|cursor)$")
    special = {k: v for k, v in gogh_theme.items() if special_regex.match(k)}

    # string that starts with color_ and has digits
    colours_regex = re.compile(r"^(color_(\d+))$")
    # string that is color_ maybe has a 0 and has digits
    key_pattern = re.compile(r"color_0?(\d+)")
    colours = {
        key_pattern.sub(r"color\1", k): v
        for k, v in gogh_theme.items()
        if colours_regex.match(k)
    }

    return [
        *special.items(),
        *util.natural_sort(colours).items(),
    ]


def get_themes():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    colourschemes_path = f"{dir_path}/themes/colorschemes/"
    themes = {}
    for theme_filename in os.listdir(colourschemes_path):
        theme_path = f"{colourschemes_path}/{theme_filename}"
        try:
            with open(theme_path) as f:
                data = json.load(f)
                colours = [
                    *data.get("special", {}).items(),
                    *util.natural_sort(data.get("colors", {})).items(),
                ]
                themes[theme_path.replace(".json", "")] = colours
        except FileNotFoundError:
            click.echo(f"could not find file: {theme_path}")

    gogh_themes_path = f"{dir_path}/themes/themes.json"
    with open(gogh_themes_path) as f:
        gogh_themes = json.load(f)
        for theme in gogh_themes:
            name = theme.get("name").replace(" ", "-")
            themes[name] = map_gogh_theme(theme)

    return themes


def get_theme(theme_name):
    return get_themes().get(theme_name, {})


@click.group()
def cli():
    pass


@cli.command()
@click.argument("theme_names", nargs=-1, type=str)
def preview(theme_names):
    """
    prints a preview of the theme
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))

    if not theme_names:
        try:
            with open(dir_path + "/current_theme") as f:
                current_theme_name = f.read().strip()
            theme_names = [current_theme_name]
        except FileNotFoundError:
            click.echo("not current theme and no theme names given")
            return

    padding = len(max(theme_names, key=len)) + 1
    for theme_name in theme_names:
        colours = get_theme(theme_name)
        if colours:
            click.echo(f"{theme_name}".ljust(padding), nl=False)
            for name, colour in colours:
                printc(name, colour)
            click.echo()
        else:
            click.echo(f"theme '{theme_name}' not found")


@cli.command()
def apply():
    """
    Applies the current theme using wallust
    """
    dir_path = os.path.dirname(os.path.realpath(__file__))
    current_theme_path = dir_path + "/current_theme"
    with open(current_theme_path) as f:
        theme_name = f.read()
    subprocess.call(f"wallust theme {theme_name}", shell=True)


@cli.command()
@click.argument("image_path", type=click.Path(writable=True))
@click.option(
    "-c",
    "--clusters",
    type=int,
    default=10,
    help="number of dominating colors in image",
)
@click.option(
    "-n",
    "--number_of_themes",
    type=int,
    default=10,
    help="number of themes to print",
)
@click.option(
    "-i",
    "--install",
    "should_install",
    is_flag=True,
    help="call interactive menu to install one of the suggested themes using wallust",
)
@click.option(
    "-p",
    "--print_palettes",
    "should_print_palettes",
    metavar="print",
    is_flag=True,
    help="print image palette (first column) and n best themes default image viewer",
    callback=lambda ctx, param, value: value,
    show_default=True,
)
def pick(
    image_path,
    clusters,
    number_of_themes,
    should_install,
    should_print_palettes,
):
    """
    Tries to pick the best color palette for a given image from
    a set of hand-picked syntax-highlighting palettes.
    """
    counts, colors = get_image_colors(image_path)
    bin_size = 1
    while len(counts) > MAX_BINS:
        bin_size *= 2
        counts, colors = colors_to_bins(counts, colors, bin_size)
    palette, importances = compute_image_palette(
        colors, counts, clusters, method="k++_pdf"
    )
    themes, scores, names = pick_best_themes(palette, importances, number_of_themes)

    if should_print_palettes is True:
        print_palettes(palette, themes)
        preview(names)

    if should_install is True:
        install_theme(names, scores)
    else:
        print_results(names, scores)


if __name__ == "__main__":
    cli()
